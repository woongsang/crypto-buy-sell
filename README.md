# [price-monitor](https://github.com/woongsang/price-monitor/) (기능이 확장됨에 따라 repo명 변경 필요)

### 데이터 저장 및 전송 ([binance_websocket.py](https://github.com/woongsang/price-monitor/blob/master/binance_websocket.py))
- .env에 명시된 `BINANCE_SOCKET_ADDR`를 통해 가격 정보를 실시간으로 수신하고, `MongoDB`에 저장한다. 저장과 동시에 `Kafka producer`를 통하여 데이터를 전송한다. `broker`는 거래소의 이름으로 설정하였다.
- 추후 여러 거래소로 확장될 것을 감안하여 `MongoDB`에는 각 거래소별로 table을 나누었다. 일정 기간이 지나면 공간 확보를 위해 오래된 데이터를 DB에서 삭제한다.

# crypto-buy-sell
### 데이터 수신 및 동작 ([kafka_consumer.py](https://github.com/woongsang/crypto-buy-sell/blob/master/kafka_consumer.py))
- `Kafka consuming`을 통해 각 사용자가 선택한 거래소 및 암호화폐 시세를 받아온다.
- 매수전략과 매도전략을 구분지어서 생각한다. 즉, 한 사용자가 원하는 매수 전략과 매도 전략을 골라 조합할 수 있도록 설계하였다. 현재는 주식시장에 쓰이는 변동성 돌파전략을 변형하여 적용한 상태이다. 하루하루 정해진 시간 내에서만 장이 열리는 주식시장과는 달리, 암호화폐 거래는 24시간 이루어진다. 따라서, 주식 시장에서의 하루와 암호화폐 시장에서의 하루의 의미는 다를 수 있음을 감안해, `cycle`이라는 설정값을 두어, 변동성 돌파전략에서의 하루를 몇 시간으로 볼 것인지 설정할 수 있게 하였다.
- [변동성 돌파전략](https://github.com/woongsang/crypto-buy-sell/blob/218773dabad730f918051aadf33154cb884734f3/buy_strategies.py#L1): 현재 `cycle`기준으로 이전 `cycle`과 비교했을 때 `long`, `short` 각각에 대한 `target price`를 제시한다. 예를들어, 현재 비트코인의 가격이 43K~44K 구간을 횡보하고 있고 45K를 뚫어야 매수 우위라고 계산될 경우 45K가 long의 `target price`가 된다. 반대로 41K가 되면 하방추세로 판단할 수 있는 경우, 41K는 short의 `target price`다. 이 함수는 두 가격을 모두 return한다.
- 현재 가격이 `target price`에 도달하면 매수 혹은 매도를 진행한다. open position, close position, SL, TP 등은 [ccxt](https://github.com/ccxt/ccxt)를 활용하여 직접 구현한 [binance_api.py](https://github.com/woongsang/crypto-buy-sell/blob/master/binance_api.py)를 활용하였다.
	 
