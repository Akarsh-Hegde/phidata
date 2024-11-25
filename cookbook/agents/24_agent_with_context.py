import json
import httpx

from phi.agent import Agent


def get_top_hackernews_stories(num_stories: int = 5) -> str:
    # Fetch top story IDs
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    # Fetch story details
    stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        story = story_response.json()
        if "text" in story:
            story.pop("text", None)
        stories.append(story)
    return json.dumps(stories)


agent = Agent(
    context={
        "name": "John Doe",
        "top_stories": lambda: get_top_hackernews_stories(3),
    },
    add_context=True,
    markdown=True,
    show_tool_calls=True,
)
agent.print_response("Who am I and what are the top stories?", stream=True)
