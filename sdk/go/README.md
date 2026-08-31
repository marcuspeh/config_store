# config_store Go SDK

HTTP client and watcher for the `config_store` service.

## Install

```bash
go get github.com/marcuspeh/config_store/sdk/go
```

## Quick start

```go
package main

import (
    "context"
    "encoding/json"
    "log"

    config "github.com/marcuspeh/config_store/sdk/go"
)

type MyServiceConfig struct {
    URL   string `json:"url"`
    Token string `json:"token"`
}

func initMyService(ctx context.Context, cfg *MyServiceConfig) (*MyService, error) {
    return NewMyService(cfg.URL, cfg.Token)
}

func main() {
    ctx := context.Background()

    client := config.NewConfigClient("my-project",
        config.WithBaseURL("http://config-store:6002"),
    )

    watcher, err := config.NewClientWatcher[MyServiceConfig, *MyService](
        ctx, client, "my-service", initMyService,
    )
    if err != nil {
        log.Fatal(err)
    }
    defer watcher.Close()

    svc := watcher.Get()
    _ = svc
}
```

## Value contract — read this

`Get(key)` returns the **raw string stored in MongoDB's `value` field, byte-for-byte.** No parsing happens on the SDK side. The `ClientWatcher` does `json.Unmarshal` the raw value into your `configStruct`, but `client.Get()` itself does not.

Implications:

| Stored in MongoDB `value` | What `client.Get("k")` returns | What `ClientWatcher` parses into `configStruct` |
|---|---|---|
| `"https://api.example.com"` (a JSON-encoded string) | the 25-char string `"https://api.example.com"` (with quotes) | your struct, `URL = "https://api.example.com"` |
| `{"url":"https://x","token":"t"}` (a JSON-encoded object) | the raw object text | your struct, fields populated |
| `42` (a JSON-encoded number) | the 2-char string `42` | your struct, integer field |

So:

- If your config is **plain text** (URL, secret, key), store the **literal string** in MongoDB — not a JSON-encoded version of it. Otherwise the SDK returns it with surrounding quotes.
- If your config is **structured**, define a `configStruct` type and pass it to `ClientWatcher`; the watcher will `json.Unmarshal` it for you. If you also need raw access, use `client.Get(key)` and parse it yourself.

## Options

```go
client := config.NewConfigClient("my-project",
    config.WithBaseURL("http://config-store:6002"),   // default: http://localhost:6002
    config.WithCacheSize(100),                        // default: 10 entries
    config.WithCacheTTL(2*time.Minute),               // default: 1m
)
```

## Error handling

- `config.ErrNotFound` — key not present in the cache.
- Any other `error` from `Get` — network failure, non-2xx response, malformed body.

`ClientWatcher` logs and continues on transient errors; it never crashes the poll loop.
