"""Alpaca (paper) execution: equity, positions, orders, prices, Darvas OTO (buy-stop + stop-loss)."""
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import StopOrderRequest, StopLossRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
import secrets_conf

_client = TradingClient(secrets_conf.ALPACA_API_KEY, secrets_conf.ALPACA_SECRET_KEY,
                        paper=secrets_conf.ALPACA_PAPER)
_data = StockHistoricalDataClient(secrets_conf.ALPACA_API_KEY, secrets_conf.ALPACA_SECRET_KEY)


def latest_price(symbol):
    try:
        r = _data.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=symbol))
        return float(r[symbol].price)
    except Exception as e:
        print(f"[broker] price {symbol} failed: {e}")
        return None


def get_equity():
    return float(_client.get_account().equity)


def open_positions_count():
    return len(_client.get_all_positions())


def open_symbols():
    return {p.symbol for p in _client.get_all_positions()}


def positions_summary():
    out = []
    for p in _client.get_all_positions():
        out.append(f"{p.symbol} x{p.qty} @ {float(p.avg_entry_price):.2f} "
                   f"(P/L ${float(p.unrealized_pl):.0f})")
    return out


def open_orders():
    return _client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))


def cancel_unheld_open_orders():
    held = open_symbols()
    n = 0
    for o in open_orders():
        if o.symbol not in held:
            try:
                _client.cancel_order_by_id(o.id)
                n += 1
            except Exception as e:
                print(f"[broker] cancel {o.symbol} failed: {e}")
    return n


def submit_darvas_order(symbol, qty, entry, stop):
    req = StopOrderRequest(
        symbol=symbol, qty=qty, side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC, stop_price=round(entry, 2),
        order_class=OrderClass.OTO,
        stop_loss=StopLossRequest(stop_price=round(stop, 2)),
    )
    return _client.submit_order(order_data=req)
