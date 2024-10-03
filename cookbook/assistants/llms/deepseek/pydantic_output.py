from phi.assistant import Assistant
from phi.llm.deepseek import DeepSeekChat
from phi.tools.yfinance import YFinanceTools
from pydantic import BaseModel, Field


class StockPrice(BaseModel):
    ticker: str = Field(..., example="NVDA")
    price: float = Field(..., example=100.0)
    currency: str = Field(..., example="USD")


assistant = Assistant(
    llm=DeepSeekChat(),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    show_tool_calls=True,
    markdown=True,
    output_model=StockPrice,
)
assistant.print_response("Write a comparison between NVDA and AMD.")
