import asyncio
import os
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)

from dotenv import load_dotenv

load_dotenv()

from app.modules.chat.agent import tutor_agent
from app.modules.resource.agents.content import content_writer
from app.modules.resource.agents.code import code_agent
from app.modules.resource.agents.mindmap import mindmap_generator
from app.modules.resource.agents.media import media_agent
from app.modules.resource.agents.ppt import ppt_agent
from app.modules.resource.agents.quiz import quiz_agent
from app.modules.resource.agents.reading import reading_agent

def get_graph_sync(agent):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(agent._ensure_graph())
        return agent.graph
    finally:
        loop.close()

tutor_graph = get_graph_sync(tutor_agent)
content_graph = get_graph_sync(content_writer)
code_graph = get_graph_sync(code_agent)
mindmap_graph = get_graph_sync(mindmap_generator)
media_graph = get_graph_sync(media_agent)
ppt_graph = get_graph_sync(ppt_agent)
quiz_graph = get_graph_sync(quiz_agent)
reading_graph = get_graph_sync(reading_agent)
