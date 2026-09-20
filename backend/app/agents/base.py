"""
Base Agent architecture for the E-Discovery platform.
Provides a foundation using LangGraph concepts with:
- Retry logic and exponential backoff
- Structured logging and metrics
- Memory
- Input validation
- JSON-only communication
- Explicit exception handling
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, Type, TypeVar, Dict

from loguru import logger
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T_Input = TypeVar("T_Input", bound=BaseModel)
T_Output = TypeVar("T_Output", bound=BaseModel)

class AgentException(Exception):
    pass

class AgentValidationException(AgentException):
    pass

class BaseAgent(ABC, Generic[T_Input, T_Output]):
    def __init__(
        self,
        name: str,
        prompt_version: str,
        input_model: Type[T_Input],
        output_model: Type[T_Output],
    ):
        self.name = name
        self.prompt_version = prompt_version
        self.input_model = input_model
        self.output_model = output_model
        self.memory: Dict[str, Any] = {}

    def _validate_input(self, data: dict | BaseModel) -> T_Input:
        try:
            if isinstance(data, BaseModel):
                return self.input_model.model_validate(data.model_dump())
            return self.input_model.model_validate(data)
        except ValidationError as e:
            logger.error(f"[{self.name}] Input validation failed: {e}")
            raise AgentValidationException(f"Invalid input: {e}")

    def _validate_output(self, data: dict | BaseModel) -> T_Output:
        try:
            if isinstance(data, BaseModel):
                return self.output_model.model_validate(data.model_dump())
            return self.output_model.model_validate(data)
        except ValidationError as e:
            logger.error(f"[{self.name}] Output validation failed: {e}")
            raise AgentValidationException(f"Invalid output format: {e}")

    @abstractmethod
    async def _execute(self, validated_input: T_Input) -> dict | T_Output:
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _execute_with_retry(self, validated_input: T_Input) -> T_Output:
        logger.debug(f"[{self.name}] Executing logic (version: {self.prompt_version})")
        result = await self._execute(validated_input)
        return self._validate_output(result)

    async def run(self, input_data: dict | BaseModel, request_id: str | None = None) -> T_Output:
        request_id = request_id or str(uuid.uuid4())
        start_time = time.perf_counter()
        
        logger.info(
            "[{name}] Agent execution started",
            name=self.name,
            request_id=request_id,
            prompt_version=self.prompt_version,
        )

        try:
            validated_input = self._validate_input(input_data)
            output = await self._execute_with_retry(validated_input)
            latency = time.perf_counter() - start_time
            confidence = getattr(output, "confidence_score", None)
            
            logger.info(
                "[{name}] Agent execution completed",
                name=self.name,
                request_id=request_id,
                latency_sec=latency,
                confidence=confidence,
            )
            
            self.memory[request_id] = {
                "input": validated_input.model_dump(),
                "output": output.model_dump(),
                "latency": latency,
            }
            
            return output
            
        except Exception as e:
            latency = time.perf_counter() - start_time
            logger.error(
                "[{name}] Agent execution failed",
                name=self.name,
                request_id=request_id,
                latency_sec=latency,
                error=str(e),
                exc_info=True,
            )
            if not isinstance(e, AgentException):
                raise AgentException(f"Agent execution failed: {str(e)}") from e
            raise
