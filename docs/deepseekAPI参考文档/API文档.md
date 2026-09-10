Chat Completions API
POST
https://api.deepseek.com/chat/completions
根据输入的上下文，来让模型补全对话内容。

Request
application/json
Body

required

messages

object[]

required

model
string
required
Possible values: [deepseek-v4-flash, deepseek-v4-pro]

使用的模型的 ID。

thinking

object

nullable

reasoning_effort
string
Possible values: [low, high, max]

控制模型的推理强度。默认为 high。出于兼容考虑 medium、xhigh 会映射为 high。请注意，目前仅 deepseek-v4-flash 支持三个思考强度档位；deepseek-v4-pro 暂时只支持 high、max 两档（low 按 high 处理，xhigh 按 max 处理），预计 2026 年 8 月初支持三档。

max_tokens
integer
nullable
限制一次请求中模型生成 completion 的最大 token 数。输入 token 和输出 token 的总长度受模型的上下文长度的限制。取值范围与默认值详见文档。

response_format

object

nullable

stop

object

nullable

stream
boolean
nullable
如果设置为 True，将会以 SSE（server-sent events）的形式以流式发送消息增量。消息流以 data: [DONE] 结尾。

stream_options

object

nullable

temperature
number
nullable
Possible values: <= 2

Default value: 1

采样温度，介于 0 和 2 之间。更高的值，如 0.8，会使输出更随机，而更低的值，如 0.2，会使其更加集中和确定。 我们通常建议可以更改这个值或者更改 top_p，但不建议同时对两者进行修改。

top_p
number
nullable
Possible values: <= 1

Default value: 1

作为调节采样温度的替代方案，模型会考虑前 top_p 概率的 token 的结果。所以 0.1 就意味着只有包括在最高 10% 概率中的 token 会被考虑。 我们通常建议修改这个值或者更改 temperature，但不建议同时对两者进行修改。

tools

object[]

nullable

tool_choice

object

nullable

logprobs
boolean
nullable
是否返回所输出 token 的对数概率。如果为 true，则在 message 的 content 中返回每个输出 token 的对数概率。

top_logprobs
integer
nullable
Possible values: <= 20

一个介于 0 到 20 之间的整数 N，指定每个输出位置返回输出概率 top N 的 token，且返回这些 token 的对数概率。指定此参数时，logprobs 必须为 true。

user_id
nullable
您自定义的 user_id，可选字符集为 [a-zA-Z0-9\-_]，最大长度为 512。请不要在 user_id 中包含用户隐私信息。

user_id 可用于区分您业务侧的用户身份，以帮助我们进行内容安全处理。
user_id 可用于 KVCache 缓存隔离，以进行隐私管理。
user_id 可用于我们对您业务侧用户进行调度隔离。
关于 user_id 参数更详细的描述，请参考限速与隔离
frequency_penalty
deprecated
该参数已不再支持。传入该参数将不会产生任何效果。

presence_penalty
deprecated
该参数已不再支持。传入该参数将不会产生任何效果。

Responses
200 (No streaming)
200 (Streaming)
OK, 返回一个 chat completion 对象。

application/json
Schema
Example (from schema)
Example
Schema

id
string
required
该对话的唯一标识符。

choices

object[]

required

created
integer
required
创建聊天完成时的 Unix 时间戳（以秒为单位）。

model
string
required
生成该 completion 的模型名。

system_fingerprint
string
required
This fingerprint represents the backend configuration that the model runs with.

object
string
required
Possible values: [chat.completion]

对象的类型, 其值为 chat.completion。

usage

object

curl
python
go
nodejs
ruby
csharp
php
java
powershell
OpenAI SDK
from openai import OpenAI

# for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
client = OpenAI(api_key="<your API key>", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
  ],
    max_tokens=1024,
    temperature=0.7,
    stream=False
)

print(response.choices[0].message.content)



REQUESTS
HTTP.CLIENT
import requests
import json

url = "https://api.deepseek.com/chat/completions"

payload = json.dumps({
  "messages": [
    {
      "content": "You are a helpful assistant",
      "role": "system"
    },
    {
      "content": "Hi",
      "role": "user"
    }
  ],
  "model": "deepseek-v4-pro",
  "thinking": {
    "type": "enabled"
  },
  "reasoning_effort": "low",
  "max_tokens": 4096,
  "response_format": {
    "type": "text"
  },
  "stop": None,
  "stream": False,
  "stream_options": None,
  "temperature": 1,
  "top_p": 1,
  "tools": None,
  "tool_choice": "none",
  "logprobs": False,
  "top_logprobs": None
})
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Authorization': 'Bearer <TOKEN>'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)


Request
Collapse all
Base URL
https://api.deepseek.com
Auth
Bearer Token
Bearer Token
Body
 required
{
  "messages": [
    {
      "content": "You are a helpful assistant",
      "role": "system"
    },
    {
      "content": "Hi",
      "role": "user"
    }
  ],
  "model": "deepseek-v4-pro",
  "thinking": {
    "type": "enabled"
  },
  "reasoning_effort": "low",
  "max_tokens": 4096,
  "response_format": {
    "type": "text"
  },
  "stop": null,
  "stream": false,
  "stream_options": null,
  "temperature": 1,
  "top_p": 1,
  "tools": null,
  "tool_choice": "none",
  "logprobs": false,
  "top_logprobs": null
}
Send API Request
Response
Clear
Click the Send API Reque