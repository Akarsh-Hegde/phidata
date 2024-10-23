from typing import Optional, Iterator

from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
from phi.workflow import Workflow
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


class GenerateNewsReport(Workflow):
    agent: Agent = Agent(
        name="Agent",
        description="Repeat the user's message back to them.",
    )

    def run_stream(self, topic: str) -> Iterator[RunResponse]:
        logger.info(f"Researching articles on: {topic}")
        yield from self.agent.run(topic, stream=True)

    def run(self, topic: str) -> RunResponse:
        logger.info(f"Researching articles on: {topic}")
        response: RunResponse = self.agent.run(topic)
        logger.info(f"Research: {response}")
        return response


generate_news_report = GenerateNewsReport(
    storage=SqlWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

report: Iterator[RunResponse] = generate_news_report.run(topic="IBM Hashicorp Acquisition")
pprint_run_response(report, markdown=True, show_time=True)
