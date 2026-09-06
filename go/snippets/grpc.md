---
id: go-grpc
title: "gRPC: сервер, клиент, статусы, ctx-таймауты"
lang: go
min_version: "1.21"
category: snippet
tags: [grpc, rpc, protobuf, server, client, status]
status: stable
updated: 2026-09-07
---

# gRPC

**Когда использовать** — service-to-service на строгих контрактах: protobuf, codegen, стриминг.
**Когда НЕ использовать** — публичный HTTP API (браузеры/мобильные): REST (см. [decisions.md](../decisions.md), [shared/api-design.md](../../shared/api-design.md)).

## Код

Контракт (`items.proto`):

```protobuf
syntax = "proto3";

package items;

service ItemService {
  rpc GetItem(GetItemRequest) returns (Item);
  rpc CreateItem(CreateItemRequest) returns (Item);
}

message GetItemRequest { int64 id = 1; }
message CreateItemRequest { string name = 1; int64 price_cents = 2; }
message Item { int64 id = 1; string name = 2; int64 price_cents = 3; }
```

Генерация (не пишите pb-код руками):

```bash
protoc --go_out=. --go_opt=paths=source_relative \
       --go-grpc_out=. --go-grpc_opt=paths=source_relative items.proto
```

Сервер:

```go
package main

import (
	"context"
	"log"
	"net"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "example.com/items/rpc"
)

type itemServer struct {
	pb.UnimplementedItemServiceServer // forward compatibility: новые методы не ломают сервер
	items                             map[int64]pb.Item
}

func (s *itemServer) GetItem(ctx context.Context, req *pb.GetItemRequest) (*pb.Item, error) {
	item, ok := s.items[req.Id]
	if !ok {
		// status.Error — не errors.New: код статуса доходит до клиента.
		return nil, status.Error(codes.NotFound, "item not found")
	}
	return item, nil
}

func (s *itemServer) CreateItem(ctx context.Context, req *pb.CreateItemRequest) (*pb.Item, error) {
	if req.Name == "" {
		return nil, status.Error(codes.InvalidArgument, "name is required")
	}
	item := &pb.Item{Id: 1, Name: req.Name, PriceCents: req.PriceCents}
	s.items[item.Id] = item
	return item, nil
}

func main() {
	srv := grpc.NewServer()
	pb.RegisterItemServiceServer(srv, &itemServer{items: map[int64]pb.Item{}})

	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatal(err)
	}
	log.Println("grpc :50051")
	if err := srv.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
```

Клиент:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "example.com/items/rpc"
)

func main() {
	conn, err := grpc.NewClient("localhost:50051") // Go 1.21+: NewClient (lazy dial)
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	client := pb.NewItemServiceClient(conn)

	// Таймаут — через context, не «где-то в настройках».
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	item, err := client.CreateItem(ctx, &pb.CreateItemRequest{Name: "Cup", PriceCents: 350})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(item)

	_, err = client.GetItem(ctx, &pb.GetItemRequest{Id: 999})
	if err != nil {
		// Декомпозиция ошибки gRPC: код + сообщение.
		st, ok := status.FromError(err)
		if ok && st.Code() == codes.NotFound {
			log.Println("not found — ожидаемо")
			return
		}
		log.Fatal(err)
	}
}
```

## Pitfalls

- **`status.Error`/`status.FromError`**, не `errors.New`/`fmt.Errorf`: иначе клиент получит `Unknown`, а не `NotFound`/`InvalidArgument`.
- **`Unimplemented*Server` встраивайте**: без него новый RPC в proto ломает старые серверы (panic вместо `Unimplemented`).
- **`grpc.NewClient` (1.21+)** вместо `grpc.Dial` (deprecated): ленивое подключение, нет «успешного dial» как гарантии доступности.
- Таймауты — только через `context` на каждый вызов; `WithBlock`-паттерны из старых туториалов — антипаттерн.
- proto3: отсутствие поля ≠ `0` ≠ `null` — для опциональных значений `optional` + presence.
- Не миксуйте REST и gRPC на одном порту без `grpc-gateway`/прокси; у них разные контракты.

## Related

- [http-server.md](http-server.md)
- [context.md](context.md)
- [error-handling.md](error-handling.md)
- [decisions.md](../decisions.md)
