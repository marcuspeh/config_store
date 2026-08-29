package config

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"
)

type ClientWatcher[configStruct any, clientStruct any] struct {
	client       *ConfigClient
	key          string
	value        any
	lastRawValue string
	initClient   func(ctx context.Context, value *configStruct) (clientStruct, error)
	mu           sync.RWMutex
	cancel       context.CancelFunc
}

func NewClientWatcher[configStruct any, clientStruct any](ctx context.Context, client *ConfigClient, key string, initClient func(ctx context.Context, value *configStruct) (clientStruct, error)) (*ClientWatcher[configStruct, clientStruct], error) {
	watchCtx, cancel := context.WithCancel(ctx)

	val, err := client.Get(watchCtx, key)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to initial fetch config key %s: %w", key, err)
	}

	w := &ClientWatcher[configStruct, clientStruct]{
		client:     client,
		key:        key,
		cancel:     cancel,
		initClient: initClient,
	}

	{
		var config configStruct
		if err := json.Unmarshal([]byte(val), &config); err != nil {
			cancel()
			return nil, fmt.Errorf("failed to unmarshal config key %s: %w", key, err)
		}

		initialized, err := w.initClient(watchCtx, &config)
		if err != nil {
			cancel()
			return nil, fmt.Errorf("failed to init client for config key %s: %w", key, err)
		}

		w.mu.Lock()
		w.value = initialized
		w.lastRawValue = val
		w.mu.Unlock()
	}

	go w.watch(watchCtx)

	return w, nil
}

func (w *ClientWatcher[configStruct, clientStruct]) watch(ctx context.Context) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			val, err := w.client.Get(ctx, w.key)
			if err != nil {
				log.Printf("failed to watch config key %s: %v", w.key, err)
				continue
			}

			w.mu.RLock()
			if val == w.lastRawValue {
				w.mu.RUnlock()
				continue
			}
			w.mu.RUnlock()

			var config configStruct
			if err := json.Unmarshal([]byte(val), &config); err != nil {
				log.Printf("failed to unmarshal config key %s: %v", w.key, err)
				continue
			}

			newValue, err := w.initClient(ctx, &config)
			if err != nil {
				log.Printf("failed to init client for config key %s: %v", w.key, err)
				continue
			}

			w.mu.Lock()
			if val == w.lastRawValue {
				w.mu.Unlock()
				if c, ok := any(newValue).(CloseClient); ok {
					c.Close()
				}
				continue
			}
			prev := w.value
			w.value = newValue
			w.lastRawValue = val
			w.mu.Unlock()

			if c, ok := any(prev).(CloseClient); ok {
				c.Close()
			}
		}
	}
}

func (w *ClientWatcher[configStruct, clientStruct]) Get() clientStruct {
	w.mu.RLock()
	defer w.mu.RUnlock()
	v, _ := w.value.(clientStruct)
	return v
}

func (w *ClientWatcher[configStruct, clientStruct]) Close() {
	w.cancel()

	w.mu.Lock()
	prev := w.value
	w.value = nil
	w.mu.Unlock()

	if c, ok := any(prev).(CloseClient); ok {
		c.Close()
	}
}

type CloseClient interface {
	Close()
}
