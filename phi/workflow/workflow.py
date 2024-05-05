from uuid import uuid4
from typing import List, Any, Optional, Dict, Iterator, Union

from pydantic import BaseModel, ConfigDict, field_validator, Field

from phi.llm.base import LLM
from phi.task.task import Task
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.message import get_text_from_message
from phi.utils.timer import Timer


class Workflow(BaseModel):
    # -*- Workflow settings
    # LLM to use for this Workflow
    llm: Optional[LLM] = None
    # Workflow name
    name: Optional[str] = None

    # -*- Run settings
    # Run UUID (autogenerated if not set)
    run_id: Optional[str] = Field(None, validate_default=True)
    # Metadata associated with this run
    run_data: Optional[Dict[str, Any]] = None

    # -*- User settings
    # ID of the user running this workflow
    user_id: Optional[str] = None
    # Metadata associated the user running this workflow
    user_data: Optional[Dict[str, Any]] = None

    # -*- Tasks in this workflow (required)
    tasks: List[Task]
    # Metadata associated with the assistant tasks
    task_data: Optional[Dict[str, Any]] = None

    # -*- Workflow Output
    # Final output of this Workflow
    output: Optional[Any] = None
    # Save the output to a file
    save_output_to_file: Optional[str] = None

    # debug_mode=True enables debug logs
    debug_mode: bool = False
    # monitoring=True logs Workflow runs on phidata.app
    monitoring: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @field_validator("run_id", mode="before")
    def set_run_id(cls, v: Optional[str]) -> str:
        return v if v is not None else str(uuid4())

    def _run(
        self,
        message: Optional[Union[List, Dict, str]] = None,
        *,
        stream: bool = True,
        **kwargs: Any,
    ) -> Iterator[str]:
        logger.debug(f"*********** Workflow Run Start: {self.run_id} ***********")

        # List of tasks that have been run
        executed_tasks: List[Task] = []
        workflow_output: List[str] = []

        # -*- Generate response by running tasks
        for idx, task in enumerate(self.tasks, start=1):
            logger.debug(f"*********** Task {idx} Start ***********")

            # -*- Prepare input message for the current_task
            task_input: List[str] = []
            if message is not None:
                task_input.append(get_text_from_message(message))

            if len(executed_tasks) > 0:
                previous_task_outputs = []
                for previous_task_idx, previous_task in enumerate(executed_tasks, start=1):
                    previous_task_output = previous_task.get_task_output_as_str()
                    if previous_task_output is not None:
                        previous_task_outputs.append(
                            (previous_task_idx, previous_task.description, previous_task_output)
                        )

                if len(previous_task_outputs) > 0:
                    task_input.append("\nHere are previous tasks and and their results:\n---")
                    for previous_task_idx, previous_task_description, previous_task_output in previous_task_outputs:
                        task_input.append(f"Task {previous_task_idx}: {previous_task_description}")
                        task_input.append(previous_task_output)
                    task_input.append("---")

            # -*- Run Task
            task_output = ""
            input_for_current_task = "\n".join(task_input)
            if stream and task.streamable:
                for chunk in task.run(message=input_for_current_task, stream=True, **kwargs):
                    task_output += chunk if isinstance(chunk, str) else ""
                    yield chunk if isinstance(chunk, str) else ""
            else:
                task_output = task.run(message=input_for_current_task, stream=False, **kwargs)  # type: ignore

            executed_tasks.append(task)
            workflow_output.append(task_output)
            logger.debug(f"*********** Task {idx} End ***********")
            if not stream:
                yield task_output

        self.output = "\n".join(workflow_output)
        if self.save_output_to_file:
            fn = self.save_output_to_file.format(name=self.name, run_id=self.run_id, user_id=self.user_id)
            with open(fn, "w") as f:
                f.write(self.output)
        logger.debug(f"*********** Workflow Run End: {self.run_id} ***********")

    def run(
        self,
        message: Optional[Union[List, Dict, str]] = None,
        *,
        stream: bool = True,
        **kwargs: Any,
    ) -> Union[Iterator[str], str]:
        if stream:
            resp = self._run(message=message, stream=True, **kwargs)
            return resp
        else:
            resp = self._run(message=message, stream=True, **kwargs)
            return next(resp)

    def print_response(
        self,
        message: Optional[Union[List, Dict, str]] = None,
        *,
        stream: bool = True,
        markdown: bool = False,
        show_message: bool = True,
        **kwargs: Any,
    ) -> None:
        from phi.cli.console import console
        from rich.live import Live
        from rich.table import Table
        from rich.status import Status
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.box import ROUNDED
        from rich.markdown import Markdown

        if stream:
            response = ""
            with Live() as live_log:
                status = Status("Working...", spinner="dots")
                live_log.update(status)
                response_timer = Timer()
                response_timer.start()
                for resp in self.run(message=message, stream=True, **kwargs):
                    if isinstance(resp, str):
                        response += resp
                    _response = Markdown(response) if markdown else response

                    table = Table(box=ROUNDED, border_style="blue", show_header=False)
                    if message and show_message:
                        table.show_header = True
                        table.add_column("Message")
                        table.add_column(get_text_from_message(message))
                    table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", _response)  # type: ignore
                    live_log.update(table)
                response_timer.stop()
        else:
            response_timer = Timer()
            response_timer.start()
            with Progress(
                SpinnerColumn(spinner_name="dots"), TextColumn("{task.description}"), transient=True
            ) as progress:
                progress.add_task("Working...")
                response = self.run(message=message, stream=False, **kwargs)  # type: ignore

            response_timer.stop()
            _response = Markdown(response) if markdown else response

            table = Table(box=ROUNDED, border_style="blue", show_header=False)
            if message and show_message:
                table.show_header = True
                table.add_column("Message")
                table.add_column(get_text_from_message(message))
            table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", _response)  # type: ignore
            console.print(table)

    def cli_app(
        self,
        user: str = "User",
        emoji: str = ":sunglasses:",
        stream: bool = True,
        markdown: bool = False,
        exit_on: Optional[List[str]] = None,
    ) -> None:
        from rich.prompt import Prompt

        _exit_on = exit_on or ["exit", "quit", "bye"]
        while True:
            message = Prompt.ask(f"[bold] {emoji} {user} [/bold]")
            if message in _exit_on:
                break

            self.print_response(message=message, stream=stream, markdown=markdown)
