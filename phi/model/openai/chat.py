from typing import Optional, List, Iterator, Dict, Any, Union, Tuple

import httpx

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.functions import get_function_call
from phi.utils.tools import get_function_call_for_tool_call

try:
    from openai import OpenAI as OpenAIClient, AsyncOpenAI as AsyncOpenAIClient
    from openai.types.completion_usage import CompletionUsage
    from openai.types.chat.chat_completion import ChatCompletion
    from openai.types.chat.chat_completion_chunk import (
        ChatCompletionChunk,
        ChoiceDelta,
        ChoiceDeltaToolCall,
    )
    from openai.types.chat.chat_completion_message import ChatCompletionMessage
except ImportError:
    logger.error("`openai` not installed")
    raise


class OpenAIChat(Model):
    """
    A class representing an OpenAI chat model.

    This class provides methods to interact with OpenAI's chat models,
    including sending requests and handling responses.
    """

    model: str = "gpt-4o"
    name: str = "OpenAIChat"
    provider: str = "OpenAI"

    # Request parameters
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Any] = None
    logprobs: Optional[bool] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    temperature: Optional[float] = None
    top_logprobs: Optional[int] = None
    user: Optional[str] = None
    top_p: Optional[float] = None
    extra_headers: Optional[Any] = None
    extra_query: Optional[Any] = None
    request_params: Optional[Dict[str, Any]] = None

    # Client parameters
    api_key: Optional[str] = None
    organization: Optional[str] = None
    base_url: Optional[Union[str, httpx.URL]] = None
    timeout: Optional[float] = None
    max_retries: Optional[int] = None
    default_headers: Optional[Any] = None
    default_query: Optional[Any] = None
    http_client: Optional[httpx.Client] = None
    client_params: Optional[Dict[str, Any]] = None

    # OpenAI clients
    client: Optional[OpenAIClient] = None
    async_client: Optional[AsyncOpenAIClient] = None

    def get_client(self) -> OpenAIClient:
        """
        Get or create an OpenAI client.

        Returns:
            OpenAIClient: An instance of the OpenAI client.
        """
        if self.client:
            return self.client

        _client_params: Dict[str, Any] = {}
        # Set client parameters if they are provided
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.organization:
            _client_params["organization"] = self.organization
        if self.base_url:
            _client_params["base_url"] = self.base_url
        if self.timeout:
            _client_params["timeout"] = self.timeout
        if self.max_retries:
            _client_params["max_retries"] = self.max_retries
        if self.default_headers:
            _client_params["default_headers"] = self.default_headers
        if self.default_query:
            _client_params["default_query"] = self.default_query
        if self.http_client:
            _client_params["http_client"] = self.http_client
        if self.client_params:
            _client_params.update(self.client_params)
        return OpenAIClient(**_client_params)

    def get_async_client(self) -> AsyncOpenAIClient:
        """
        Get or create an asynchronous OpenAI client.

        Returns:
            AsyncOpenAIClient: An instance of the asynchronous OpenAI client.
        """
        if self.async_client:
            return self.async_client

        _client_params: Dict[str, Any] = {}
        # Set client parameters if they are provided
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.organization:
            _client_params["organization"] = self.organization
        if self.base_url:
            _client_params["base_url"] = self.base_url
        if self.timeout:
            _client_params["timeout"] = self.timeout
        if self.max_retries:
            _client_params["max_retries"] = self.max_retries
        if self.default_headers:
            _client_params["default_headers"] = self.default_headers
        if self.default_query:
            _client_params["default_query"] = self.default_query
        if self.http_client:
            _client_params["http_client"] = self.http_client
        else:
            # Create a new async HTTP client with custom limits
            _client_params["http_client"] = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=1000, max_keepalive_connections=100)
            )
        if self.client_params:
            _client_params.update(self.client_params)
        return AsyncOpenAIClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        """
        Generate keyword arguments for API requests.

        Returns:
            Dict[str, Any]: A dictionary of keyword arguments for API requests.
        """
        _request_params: Dict[str, Any] = {}
        # Set request parameters if they are provided
        if self.frequency_penalty:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias:
            _request_params["logit_bias"] = self.logit_bias
        if self.logprobs:
            _request_params["logprobs"] = self.logprobs
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.presence_penalty:
            _request_params["presence_penalty"] = self.presence_penalty
        if self.response_format:
            _request_params["response_format"] = self.response_format
        if self.seed:
            _request_params["seed"] = self.seed
        if self.stop:
            _request_params["stop"] = self.stop
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.top_logprobs:
            _request_params["top_logprobs"] = self.top_logprobs
        if self.user:
            _request_params["user"] = self.user
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.extra_headers:
            _request_params["extra_headers"] = self.extra_headers
        if self.extra_query:
            _request_params["extra_query"] = self.extra_query
        if self.tools:
            _request_params["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _request_params["tool_choice"] = "auto"
            else:
                _request_params["tool_choice"] = self.tool_choice
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the OpenAIChat instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the OpenAIChat instance.
        """
        _dict = super().to_dict()
        # Add class-specific attributes to the dictionary
        if self.frequency_penalty:
            _dict["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias:
            _dict["logit_bias"] = self.logit_bias
        if self.logprobs:
            _dict["logprobs"] = self.logprobs
        if self.max_tokens:
            _dict["max_tokens"] = self.max_tokens
        if self.presence_penalty:
            _dict["presence_penalty"] = self.presence_penalty
        if self.response_format:
            _dict["response_format"] = self.response_format
        if self.seed:
            _dict["seed"] = self.seed
        if self.stop:
            _dict["stop"] = self.stop
        if self.temperature:
            _dict["temperature"] = self.temperature
        if self.top_logprobs:
            _dict["top_logprobs"] = self.top_logprobs
        if self.user:
            _dict["user"] = self.user
        if self.top_p:
            _dict["top_p"] = self.top_p
        if self.extra_headers:
            _dict["extra_headers"] = self.extra_headers
        if self.extra_query:
            _dict["extra_query"] = self.extra_query
        if self.tools:
            _dict["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _dict["tool_choice"] = "auto"
            else:
                _dict["tool_choice"] = self.tool_choice
        return _dict

    def invoke(self, messages: List[Message]) -> ChatCompletion:
        """
        Send a chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        return self.get_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            **self.api_kwargs,
        )

    async def ainvoke(self, messages: List[Message]) -> ChatCompletion:
        """
        Asynchronously send a chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        return await self.get_async_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            **self.api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[ChatCompletionChunk]:
        """
        Send a streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            Iterator[ChatCompletionChunk]: An iterator of chat completion chunks.
        """
        yield from self.get_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            stream_options={"include_usage": True},
            **self.api_kwargs,
        )  # type: ignore

    async def ainvoke_stream(self, messages: List[Message]) -> Any:
        """
        Asynchronously send a streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            Any: An asynchronous iterator of chat completion chunks.
        """
        async_stream = await self.get_async_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )
        async for chunk in async_stream:  # type: ignore
            yield chunk

    def _log_messages(self, messages: List[Message]) -> None:
        for m in messages:
            m.log()

    def _update_usage_metrics(self, agent_message: Message, response_usage: Optional[CompletionUsage]) -> None:
        """
        Update the usage metrics for the assistant message.

        Args:
            agent_message (Message): The assistant message.
            response_usage (Optional[CompletionUsage]): The response usage.
        """
        if response_usage:
            prompt_tokens = response_usage.prompt_tokens
            completion_tokens = response_usage.completion_tokens
            total_tokens = response_usage.total_tokens

            if prompt_tokens is not None:
                agent_message.metrics["prompt_tokens"] = prompt_tokens
                agent_message.metrics["input_tokens"] = prompt_tokens
                self.metrics["prompt_tokens"] = self.metrics.get("prompt_tokens", 0) + prompt_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + prompt_tokens
            if completion_tokens is not None:
                agent_message.metrics["completion_tokens"] = completion_tokens
                agent_message.metrics["output_tokens"] = completion_tokens
                self.metrics["completion_tokens"] = self.metrics.get("completion_tokens", 0) + completion_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + completion_tokens
            if total_tokens is not None:
                agent_message.metrics["total_tokens"] = total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

    def _handle_tool_calls(
        self, agent_message: Message, messages: List[Message], model_response: ModelResponse
    ) -> Optional[ModelResponse]:
        """
        Handle tool calls in the assistant message.

        Args:
            agent_message (Message): The assistant message.
            messages (List[Message]): The list of messages.
            model_response (ModelResponse): The model response.

        Returns:
            Optional[ModelResponse]: The model response after handling tool calls.
        """
        if agent_message.tool_calls is not None and self.run_tools:
            model_response.content = ""
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content="Could not find function to call.",
                        )
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content=_function_call.error,
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                calls_str = "\n".join(f" - Running: {_f.get_call_str()}" for _f in function_calls_to_run)
                model_response.content += f"\n{calls_str}\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            return model_response
        return None

    def _create_agent_message(
        self,
        response_message: ChatCompletionMessage,
        response_timer: Timer,
        response_usage: Optional[CompletionUsage],
    ) -> Message:
        """
        Create an assistant message from the response message.

        Args:
            response_message (ChatCompletionMessage): The response message.
            response_timer (Timer): The response timer.
            response_usage (Optional[CompletionUsage]): The response usage.

        Returns:
            Message: The assistant message.
        """
        agent_message = Message(
            role=response_message.role or "assistant",
            content=response_message.content,
        )
        if response_message.tool_calls is not None:
            agent_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]

        agent_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        self._update_usage_metrics(agent_message, response_usage)
        return agent_message

    # Refactored response method
    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Send a chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            ModelResponse: The model response from the API.
        """
        logger.debug("---------- OpenAI Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: ChatCompletion = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        response_message: ChatCompletionMessage = response.choices[0].message
        response_usage: Optional[CompletionUsage] = response.usage

        agent_message = self._create_agent_message(response_message, response_timer, response_usage)
        messages.append(agent_message)
        agent_message.log()

        if self._handle_tool_calls(agent_message, messages, model_response):
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                model_response.content += response_after_tool_calls.content
            return model_response

        if agent_message.content is not None:
            model_response.content = agent_message.get_content_string()

        logger.debug("---------- OpenAI Response End ----------")
        return model_response

    # Refactored aresponse method
    async def aresponse(self, messages: List[Message]) -> ModelResponse:
        """
        Asynchronously send a chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            ModelResponse: The model response from the API.
        """
        logger.debug("---------- OpenAI Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: ChatCompletion = await self.ainvoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        response_message: ChatCompletionMessage = response.choices[0].message
        response_usage: Optional[CompletionUsage] = response.usage

        agent_message = self._create_agent_message(response_message, response_timer, response_usage)
        messages.append(agent_message)
        agent_message.log()

        if self._handle_tool_calls(agent_message, messages, model_response):
            response_after_tool_calls = await self.aresponse(messages=messages)
            if response_after_tool_calls.content is not None:
                model_response.content += response_after_tool_calls.content
            return model_response

        if agent_message.content is not None:
            model_response.content = agent_message.get_content_string()

        logger.debug("---------- OpenAI Async Response End ----------")
        return model_response

    # Additional helper methods for streaming responses
    def _initialize_stream_variables(self):
        """
        Initialize the variables for the streaming response.

        Returns:
            Dict[str, Any]: The variables dictionary.
        """
        return {
            "agent_message_content": "",
            "agent_message_tool_calls": None,
            "completion_tokens": 0,
            "response_prompt_tokens": 0,
            "response_completion_tokens": 0,
            "response_total_tokens": 0,
            "time_to_first_token": None,
            "response_timer": Timer(),
        }

    def _update_stream_metrics(self, vars_dict, agent_message):
        """
        Update the metrics for the streaming response.

        Args:
            vars_dict (Dict[str, Any]): The variables dictionary.
            agent_message (Message): The assistant message.
        """
        response_timer = vars_dict["response_timer"]
        completion_tokens = vars_dict["completion_tokens"]
        time_to_first_token = vars_dict["time_to_first_token"]
        response_prompt_tokens = vars_dict["response_prompt_tokens"]
        response_completion_tokens = vars_dict["response_completion_tokens"]
        response_total_tokens = vars_dict["response_total_tokens"]

        agent_message.metrics["time"] = response_timer.elapsed
        if time_to_first_token is not None:
            agent_message.metrics["time_to_first_token"] = f"{time_to_first_token:.4f}s"
        if completion_tokens > 0:
            agent_message.metrics["time_per_output_token"] = f"{response_timer.elapsed / completion_tokens:.4f}s"

        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        if time_to_first_token is not None:
            if "time_to_first_token" not in self.metrics:
                self.metrics["time_to_first_token"] = []
            self.metrics["time_to_first_token"].append(f"{time_to_first_token:.4f}s")
        if completion_tokens > 0:
            if "tokens_per_second" not in self.metrics:
                self.metrics["tokens_per_second"] = []
            self.metrics["tokens_per_second"].append(f"{completion_tokens / response_timer.elapsed:.4f}")

        agent_message.metrics["prompt_tokens"] = response_prompt_tokens
        agent_message.metrics["input_tokens"] = response_prompt_tokens
        self.metrics["prompt_tokens"] = self.metrics.get("prompt_tokens", 0) + response_prompt_tokens
        self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + response_prompt_tokens

        agent_message.metrics["completion_tokens"] = response_completion_tokens
        agent_message.metrics["output_tokens"] = response_completion_tokens
        self.metrics["completion_tokens"] = self.metrics.get("completion_tokens", 0) + response_completion_tokens
        self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + response_completion_tokens

        agent_message.metrics["total_tokens"] = response_total_tokens
        self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + response_total_tokens

    # Refactored response_stream method
    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Send a streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            Iterator[ModelResponse]: An iterator of model responses.
        """
        logger.debug("---------- OpenAI Response Start ----------")
        self._log_messages(messages)

        vars_dict = self._initialize_stream_variables()
        vars_dict["response_timer"].start()

        for response in self.invoke_stream(messages=messages):
            if len(response.choices) > 0:
                response_delta: ChoiceDelta = response.choices[0].delta
                response_content = response_delta.content
                response_tool_calls = response_delta.tool_calls

                if response_content is not None:
                    vars_dict["agent_message_content"] += response_content
                    vars_dict["completion_tokens"] += 1
                    if vars_dict["completion_tokens"] == 1:
                        vars_dict["time_to_first_token"] = vars_dict["response_timer"].elapsed
                        logger.debug(f"Time to first token: {vars_dict['time_to_first_token']:.4f}s")
                    yield ModelResponse(content=response_content)

                if response_tool_calls is not None:
                    if vars_dict["agent_message_tool_calls"] is None:
                        vars_dict["agent_message_tool_calls"] = []
                    vars_dict["agent_message_tool_calls"].extend(response_tool_calls)

                if response.usage:
                    response_usage: Optional[CompletionUsage] = response.usage
                    if response_usage:
                        vars_dict["response_prompt_tokens"] = response_usage.prompt_tokens
                        vars_dict["response_completion_tokens"] = response_usage.completion_tokens
                        vars_dict["response_total_tokens"] = response_usage.total_tokens

        vars_dict["response_timer"].stop()
        completion_tokens = vars_dict["completion_tokens"]
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {vars_dict['response_timer'].elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / vars_dict['response_timer'].elapsed:.4f} tokens/s")

        agent_message = Message(role="assistant")
        if vars_dict["agent_message_content"] != "":
            agent_message.content = vars_dict["agent_message_content"]

        if vars_dict["agent_message_tool_calls"] is not None:
            # Build tool calls (simplified for brevity)
            agent_message.tool_calls = self._build_tool_calls(vars_dict["agent_message_tool_calls"])

        self._update_stream_metrics(vars_dict, agent_message)
        messages.append(agent_message)
        agent_message.log()

        if agent_message.tool_calls is not None and self.run_tools:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content="Could not find function to call.",
                        )
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content=_function_call.error,
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                for _f in function_calls_to_run:
                    yield ModelResponse(content=f"\n - Running: {_f.get_call_str()}\n\n")

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            yield from self.response_stream(messages=messages)
        logger.debug("---------- OpenAI Response End ----------")

    # Similar refactoring applied to aresponse_stream method
    async def aresponse_stream(self, messages: List[Message]) -> Any:
        """
        Asynchronously send a streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of message objects representing the conversation.

        Returns:
            Any: An asynchronous iterator of chat completion chunks.
        """
        logger.debug("---------- OpenAI Async Response Start ----------")
        self._log_messages(messages)

        vars_dict = self._initialize_stream_variables()
        vars_dict["response_timer"].start()
        async_stream = self.ainvoke_stream(messages=messages)

        async for response in async_stream:
            if len(response.choices) > 0:
                response_delta: ChoiceDelta = response.choices[0].delta
                response_content = response_delta.content
                response_tool_calls = response_delta.tool_calls

                if response_content is not None:
                    vars_dict["agent_message_content"] += response_content
                    vars_dict["completion_tokens"] += 1
                    if vars_dict["completion_tokens"] == 1:
                        vars_dict["time_to_first_token"] = vars_dict["response_timer"].elapsed
                        logger.debug(f"Time to first token: {vars_dict['time_to_first_token']:.4f}s")
                    yield response_content

                if response_tool_calls is not None:
                    if vars_dict["agent_message_tool_calls"] is None:
                        vars_dict["agent_message_tool_calls"] = []
                    vars_dict["agent_message_tool_calls"].extend(response_tool_calls)

        vars_dict["response_timer"].stop()
        completion_tokens = vars_dict["completion_tokens"]
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {vars_dict['response_timer'].elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / vars_dict['response_timer'].elapsed:.4f} tokens/s")

        agent_message = Message(role="assistant")
        if vars_dict["agent_message_content"] != "":
            agent_message.content = vars_dict["agent_message_content"]

        if vars_dict["agent_message_tool_calls"] is not None:
            agent_message.tool_calls = self._build_tool_calls(vars_dict["agent_message_tool_calls"])

        self._update_stream_metrics(vars_dict, agent_message)
        messages.append(agent_message)
        agent_message.log()

        if agent_message.tool_calls is not None and self.run_tools:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content="Could not find function to call.",
                        )
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content=_function_call.error,
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                for _f in function_calls_to_run:
                    yield f"\n - Running: {_f.get_call_str()}\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            async for content in self.aresponse_stream(messages=messages):
                yield content
        logger.debug("---------- OpenAI Async Response End ----------")

    def _build_tool_calls(self, tool_calls_data: List[ChoiceDeltaToolCall]) -> List[Dict[str, Any]]:
        """
        Build tool calls from tool call data.

        Args:
            tool_calls_data (List[ChoiceDeltaToolCall]): The tool call data to build from.

        Returns:
            List[Dict[str, Any]]: The built tool calls.
        """
        tool_calls: List[Dict[str, Any]] = []
        for _tool_call in tool_calls_data:
            _index = _tool_call.index
            _tool_call_id = _tool_call.id
            _tool_call_type = _tool_call.type
            _function_name = _tool_call.function.name if _tool_call.function else None
            _function_arguments = _tool_call.function.arguments if _tool_call.function else None

            if len(tool_calls) <= _index:
                tool_calls.extend([{}] * (_index - len(tool_calls) + 1))
            tool_call_entry = tool_calls[_index]
            if not tool_call_entry:
                tool_call_entry["id"] = _tool_call_id
                tool_call_entry["type"] = _tool_call_type
                tool_call_entry["function"] = {
                    "name": _function_name or "",
                    "arguments": _function_arguments or "",
                }
            else:
                if _function_name:
                    tool_call_entry["function"]["name"] += _function_name
                if _function_arguments:
                    tool_call_entry["function"]["arguments"] += _function_arguments
                if _tool_call_id:
                    tool_call_entry["id"] = _tool_call_id
                if _tool_call_type:
                    tool_call_entry["type"] = _tool_call_type
        return tool_calls

    def run_function(self, function_call: Dict[str, Any]) -> Tuple[Message, Optional[FunctionCall]]:
        """
        Run a function call.

        Args:
            function_call (Dict[str, Any]): The function call to run.

        Returns:
            Tuple[Message, Optional[FunctionCall]]: The function call message and the function call.
        """
        _function_name = function_call.get("name")
        _function_arguments_str = function_call.get("arguments")
        if _function_name is not None:
            # Get function call
            _function_call = get_function_call(
                name=_function_name,
                arguments=_function_arguments_str,
                functions=self.functions,
            )
            if _function_call is None:
                return Message(role="function", content="Could not find function to call."), None
            if _function_call.error is not None:
                return Message(role="function", tool_call_error=True, content=_function_call.error), _function_call

            if self.function_call_stack is None:
                self.function_call_stack = []

            # -*- Check function call limit
            if self.tool_call_limit and len(self.function_call_stack) > self.tool_call_limit:
                self.tool_choice = "none"
                return Message(
                    role="function",
                    content=f"Function call limit ({self.tool_call_limit}) exceeded.",
                ), _function_call

            # -*- Run function call
            self.function_call_stack.append(_function_call)
            _function_call_timer = Timer()
            _function_call_timer.start()
            function_call_success = _function_call.execute()
            _function_call_timer.stop()
            _function_call_message = Message(
                role="function",
                name=_function_call.function.name,
                content=_function_call.result if function_call_success else _function_call.error,
                tool_call_error=not function_call_success,
                metrics={"time": _function_call_timer.elapsed},
            )
            if "function_call_times" not in self.metrics:
                self.metrics["function_call_times"] = {}
            if _function_call.function.name not in self.metrics["function_call_times"]:
                self.metrics["function_call_times"][_function_call.function.name] = []
            self.metrics["function_call_times"][_function_call.function.name].append(_function_call_timer.elapsed)
            return _function_call_message, _function_call
        return Message(role="function", content="Function name is None."), None
