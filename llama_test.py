import asyncio
import time
import subprocess
import os
import httpx
import re
from openai import AsyncOpenAI
from pathlib import Path

# Configuration for green
CARBON_INTENSITY = 475 # Grams CO2 per kWh (Global average)
# State for energy monitoring
monitor_data = {"total_mw": 0.0, "samples": 0}
monitoring_active = False

client = AsyncOpenAI(base_url="http://localhost:8080/v1", api_key="sk-no-key-required")
benchmark_results = []

# --- Energy Monitoring Logic ---

async def monitor_m4_power():
    """Polls M4 sensors for combined CPU/GPU/ANE power draw."""
    global monitoring_active
    while monitoring_active:
        try:
            # -i 250: sample every 250ms. -n 1: single snapshot.
            res = subprocess.check_output(
                ["sudo", "powermetrics", "-i", "250", "-n", "1", "--samplers", "cpu_power"],
                stderr=subprocess.STDOUT
            ).decode()
            
            match = re.search(r"Combined Power \(CPU \+ GPU \+ ANE\): (\d+) mW", res)
            if match:
                monitor_data["total_mw"] += float(match.group(1))
                monitor_data["samples"] += 1
        except Exception:
            pass
        await asyncio.sleep(0.25)

def calculate_co2(joules):
    kwh = joules / 3_600_000
    return kwh * CARBON_INTENSITY

def get_offset_equivalents(co2_grams):
    # Tree absorption per minute (approx)
    # A tree abosorbs around 21kg per year
    # So that's 21,000,000mg per 525,600 minutes
    # 21kg/year / 525,600 minutes
    tree_minutes = co2_grams / (21000000 / 525600)
    
    # LED 9W bulb hours (assuming global avg grid)
    # 9W LED for 1 hour uses 0.009 kWh.
    # At 475g CO2/kWh, 1 hour of light = 4,275 mg of CO2
    # 4,275mg / 60 minutes = ~71.25mg per minute
    bulb_minutes = co2_grams / 71.25 
    
    return tree_minutes, bulb_minutes


# Configuration
LLAMA_SERVER_PATH = "./.appdata/build/llama.cpp/bin/llama-server"
MODEL_PATH = Path("/Volumes/Corpora/LLMs/Qwen/Qwen3-8B-Q8_0.gguf").expanduser().resolve()
SYSTEM_PROMPT = "Here is some writing: I went to Tokyo once. It was lovely. I really want to go there again. I wish my friends had come with me. I was lonely. I don't like being lonely. So I wanted to die. But I didn't. I was relieved. Thank you for reading. I had a lovely time."
TASKS = ["As a kind teacher, give feedback on how interesting the writing above is. Be very brief.",
         "As a critical reviewer, say what is wrong with the writing. Be super brief.",
         "As someone curious about language choice, ask questions about the writing. Be crazy brief."]

client = AsyncOpenAI(base_url="http://localhost:8080/v1", api_key="sk-no-key-required")
benchmark_data = []

def start_llama_server():
    """
    Starts the llama.cpp server with M4 optimized flags.
    -ngl 99: Offload all layers to GPU (Metal).
    -c 8192: Total context size (adjust based on task length).
    -np 10: 10 parallel slots for the 10 tasks.
    --cache-prompt: Enable KV cache reuse for the system prompt.
    """
    command = [
        LLAMA_SERVER_PATH,
        "-m", MODEL_PATH,
        "-ngl", "99",
        "-c", "8192",
        "-np", str(len(TASKS)),
        "--jinja",
        "--cache-prompt",
        "--port", "8080",
        "--flash-attn"
    ]
    # Start the process and let it run in the background
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def wait_for_server(url="http://localhost:8080/health", timeout=60):
    """Pings the health endpoint until the server is ready."""
    start_time = time.time()
    print("Waiting for llama-server to initialize...")
    while time.time() - start_time < timeout:
        try:
            # The health endpoint returns 200 when ready
            response = httpx.get(url)
            if response.status_code == 200:
                print(f"Server ready! (Took {time.time() - start_time:.2f}s)")
                return True
        except httpx.RequestError:
            # Server hasn't even started the networking stack yet
            pass
        time.sleep(0.5)
    raise TimeoutError("llama-server failed to start within the timeout period.")

async def run_single_task(task_content):
    try:
        response = await client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task_content},
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

async def run_task_with_stats(task_id, task_content, stream=False, thinking=False):
    """Sends task and extracts OpenAI-style usage statistics. If stream=True, prints output in real-time."""
    start = time.perf_counter()
    tokens = 0

    # 1. Toggle Thinking Mode using Qwen3's specific tags
    trigger = "/think" if thinking else "/no_think"
    prompt_with_trigger = f"{task_content} {trigger}"

    # 2. Apply best practice sampling parameters for Qwen3
    params = {
        "temperature": 0.6 if thinking else 0.7,
        "top_p": 0.95 if thinking else 0.8,
        "presence_penalty": 1.5,
        "extra_body": {
            "top_k": 20,
            "min_p": 0
        }
    }

    try:
        response = await client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_with_trigger}
            ],
            stream=stream,
            # include_usage ensures the final chunk contains token counts
            stream_options={"include_usage": True} if stream else None,
            **params # Unpack the recommended settings
        )

        is_thinking = False
        if stream:
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None

                # 1. Check for dedicated reasoning field (Modern Qwen3 Spec)
                reasoning = getattr(delta, 'reasoning_content', None)
                if reasoning:
                    if not is_thinking:
                        print(f"\n\033[94m[Task {task_id} REASONING]\033[0m > ", end="", flush=True)
                        is_thinking = True
                    print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                    continue
                
                # 2. Check regular content field (Classic Tag Spec)
                content = getattr(delta, 'content', None)
                if content:
                    if is_thinking:
                        print(f"\n\033[94m[Task {task_id} RESPONSE]\033[0m > ", end="", flush=True)
                        is_thinking = False
                    print(f"{content}", end="", flush=True)
                    continue
                
                if chunk.usage:
                    tokens = chunk.usage.completion_tokens
            print(f"\n[Task {task_id}] FINISHED")
        else:
            # For non-streaming
            full_text = response.choices[0].message.content
            tokens = response.usage.completion_tokens
            print(f"\n[Task {task_id} Full Output]:\n{full_text}")

        latency = time.perf_counter() - start
        tps = tokens / latency if latency > 0 else 0
        return tokens, tps
    except Exception as e:
        print(f"\nTask {task_id} failed: {e}")
        return 0, 0

### TEST 1: PARALLEL EXECUTION
async def test_parallel():
    print(f"--- Starting Parallel Test ({len(TASKS)} tasks) ---")
    start_time = time.perf_counter()
    
    # asyncio.gather fires all requests at once; llama-server handles the batching
    results = await asyncio.gather(*(run_task_with_stats(t) for t in TASKS))
    print(results)
    
    end_time = time.perf_counter()
    print(f"Parallel Total Time: {end_time - start_time:.2f} seconds")
    return results

### TEST 2: SEQUENTIAL EXECUTION
async def test_sequential():
    print(f"--- Starting Sequential Test ({len(TASKS)} tasks) ---")
    start_time = time.perf_counter()
    
    results = []
    for t in TASKS:
        res = await run_task_with_stats(t)
        results.append(res)
        
    end_time = time.perf_counter()
    print(f"Sequential Total Time: {end_time - start_time:.2f} seconds")
    return results

### TEST LOGIC
async def run_benchmark(mode="parallel", stream=False, thinking=False):

    global monitoring_active, monitor_data

    print(f"\n--- Running {mode.upper()} Test ---")

    # Start monitoring
    monitor_data = {"total_mw": 0.0, "samples": 0}
    monitoring_active = True
    monitor_task = asyncio.create_task(monitor_m4_power())

    start_total = time.perf_counter()

    if mode == "parallel":
        # Launch all 10 simultaneously
        results = await asyncio.gather(*(run_task_with_stats(i, t, stream=stream, thinking=thinking) for i, t in enumerate(TASKS)))
    else:
        # Run 10 one after another
        results = []
        for i, t in enumerate(TASKS):
            results.append(await run_task_with_stats(i, t, stream=stream, thinking=thinking))
    
    end_total = time.perf_counter()

    # Stop monitoring
    monitoring_active = False
    await monitor_task

    # Calculate aggregate stats
    total_tokens = sum(r[0] for r in results)
    avg_tps = sum(r[1] for r in results) / len(results)
    total_time = end_total - start_total
    actual_throughput = total_tokens / total_time

    # Energy calculations
    average_mw = monitor_data["total_mw"] / monitor_data["samples"] if monitor_data["samples"] > 0 else 0
    total_joules = (average_mw * total_time) / 1000
    co2_mg = calculate_co2(total_joules) * 1000 # Convert to milligrams for readability
    tree_mins, bulb_mins = get_offset_equivalents(co2_mg)

    benchmark_data.append({
        "Mode": f"{mode.capitalize()} (Stream={stream})",
        "Total Time (s)": f"{total_time:.2f}",
        "Tokens": total_tokens,
        "Throughput (t/s)": f"{actual_throughput:.2f} t/s",
        "Energy (J)": f"{total_joules:.1f}",
        "CO2 (mg)": f"{co2_mg:.2f}",
        "Tree Offset": f"{tree_mins:.2f} mins",
        "Lightbulb": f"{bulb_mins:.1f} mins"
    })

def print_markdown_table(data):
    """Prints a clean markdown table of the results."""
    if not data: return
    headers = data[0].keys()
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    print(f"\n### Benchmark Results\n{header_row}\n{sep_row}")
    for row in data:
        print("| " + " | ".join(str(row[h]) for h in headers) + " |")

async def main():
    server = None
    try:
        server = start_llama_server()
        wait_for_server()

        # Compare them
        await run_benchmark(mode="sequential", stream=True, thinking=True)
        await run_benchmark(mode="parallel", stream=True, thinking=True)
        await run_benchmark(mode="sequential", stream=True, thinking=False)
        await run_benchmark(mode="parallel", stream=True, thinking=False)

        print_markdown_table(benchmark_data)

    finally:
        if server:
            print("\nShutting down server...")
            server.terminate()
            server.wait()

if __name__ == "__main__":
    # Change to "sequential" to compare the difference
    asyncio.run(main())