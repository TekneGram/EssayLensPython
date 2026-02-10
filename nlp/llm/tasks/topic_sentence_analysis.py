# start here
"""
Topic Sentence Analysis Task

This task defines a system prompt that explains what a topic sentence is and
instructs the model to judge whether the topic sentence in a paragraph is good.
It also provides a small set of short paragraph tasks for evaluation.
"""

SYSTEM_PROMPT = (
    "Topic sentence: A topic sentence is usually the first sentence of a paragraph. "
    "It states the main or controlling idea of the paragraph and tells the reader what "
    "the paragraph will be about. A good topic sentence is clear, specific, and focused, "
    "and it matches the content of the sentences that follow. "
    "Your task is to judge whether the topic sentence in the paragraph is a good topic "
    "sentence. Decide whether it clearly expresses the main idea and appropriately "
    "introduces the paragraph."
)

TASKS = [
    "Online learning has become more popular in recent years. Many universities now offer "
    "full degree programs online, allowing students to study from anywhere. This flexibility "
    "is especially helpful for working adults and international students.",

    "There are many different animals in the world. Penguins, for example, live in cold regions "
    "and cannot fly, while elephants live in warmer climates and are the largest land animals.",

    "Regular exercise has important benefits for mental health. Physical activity can reduce "
    "stress, improve mood, and help people manage anxiety and depression more effectively."
]