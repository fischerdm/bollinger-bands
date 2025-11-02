import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from typing import Optional

class Plotter:
    """Handles visualization of financial data and indicators."""

    def __init__(self):
        self.fig = None

    def plot_candlestick(
        self,
        data: pd.DataFrame, 
        line_color: Optional[str] = None 
    ) -> None:
        """Plots the price chart for the given ticker."""
        self.fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],

            # Set the body fill colors (e.g., green for up, red for down)
            increasing_fillcolor='green',
            decreasing_fillcolor='red',
            
            # Set the line color for increasing candles to black
            increasing_line_color = "black" if line_color == "black" else "green" if line_color is None else line_color,

            # Set the line color for decreasing candles to black
            decreasing_line_color='black' if line_color == "black" else "red" if line_color is None else line_color
        )])

        self.fig.update_layout(
            title=f"{data.attrs['ticker']} Candlestick Chart",
            yaxis_title="Price",
            xaxis_rangeslider_visible=True # False
        )

        return self.fig

    def add_moving_average(self, ma_values, name='MA'):
        if self.fig is None:
            raise ValueError("Create a plot first using plot_candlestick()")
        
        self.fig.add_trace(go.Scatter(
            x=ma_values.index,
            y=ma_values,
            name=name,
            line=dict(color='black', width=2)
        ))
        return self.fig
    
    def add_bollinger_bands(self, bb_values, name_prefix='BB', dashed=False):
        if self.fig is None:
            raise ValueError("Create a plot first using plot_candlestick()")
        
        self.fig.add_trace(go.Scatter(
            x=bb_values['upper'].index,
            y=bb_values['upper'],
            name=f'{name_prefix} Upper',
            line=dict(color='blue', 
                      width=1,
                      dash='dash' if dashed else 'solid'),
            opacity=0.5
        ))
        
        # self.fig.add_trace(go.Scatter(
        #     x=bb_values['middle'].index,
        #     y=bb_values['middle'],
        #     name=f'{name_prefix} Middle',
        #     line=dict(color='blue', width=1),
        #     opacity=0.5
        # ))
        
        self.fig.add_trace(go.Scatter(
            x=bb_values['lower'].index,
            y=bb_values['lower'],
            name=f'{name_prefix} Lower',
            line=dict(color='blue', 
                      width=1,
                      dash='dash' if dashed else 'solid'),
            opacity=0.5
        ))
        
        return self.fig


    def show(self):
        if self.fig is None:
            raise ValueError("No plot to show")
        self.fig.show()
        
        
    # def plot_bollinger_bands(
    #     self,
    #     monthly_data: pd.DataFrame,
    #     ticker: str,
    #     windows: list = [20, 40],
    #     figsize: tuple = (15, 6)
    # ) -> None:
    #     """Plots Bollinger Bands for the given ticker and windows."""
    #     fig, ax = plt.subplots(figsize=figsize)
    #     ax.plot(monthly_data[ticker], label=f'{ticker} Price (monthly)')

    #     for window in windows:
    #         ax.plot(monthly_data[f'middle_bb_{window}m'], label=f'{window}M Middle BB', linestyle='--')
    #         ax.plot(monthly_data[f'upper_bb_{window}m'], label=f'{window}M Upper BB', linestyle='--', color='red')
    #         ax.plot(monthly_data[f'lower_bb_{window}m'], label=f'{window}M Lower BB', linestyle='--', color='green')
    #         ax.fill_between(
    #             monthly_data.index,
    #             monthly_data[f'lower_bb_{window}m'],
    #             monthly_data[f'upper_bb_{window}m'],
    #             alpha=0.1,
    #             color='grey'
    #         )

    #     ax.set_title(f'Monthly Bollinger Bands for {ticker}')
    #     ax.set_ylabel('Price (USD)')
    #     ax.legend()
    #     plt.tight_layout()
    #     plt.show()

    # def plot_relative_strength(
    #     self,
    #     monthly_data: pd.DataFrame,
    #     ticker: str,
    #     benchmark: str,
    #     figsize: tuple = (15, 6)
    # ) -> None:
    #     """Plots relative strength between ticker and benchmark."""
    #     fig, ax = plt.subplots(figsize=figsize)
    #     ax.plot(monthly_data['relative_strength'], label=f'Relative Strength ({ticker} / {benchmark})', color='purple')
    #     ax.axhline(1, color='black', linestyle=':', label='Benchmark Level')
    #     ax.set_title(f'Relative Strength of {ticker} vs. {benchmark}')
    #     ax.set_ylabel('Relative Strength')
    #     ax.legend()
    #     plt.tight_layout()
    #     plt.show()
