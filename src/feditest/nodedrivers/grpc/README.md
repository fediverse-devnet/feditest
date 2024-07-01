# GRPC Node Client

This is an experimental PoC for GRPC access to a GRPC-enabled Feditest Node.

## Protobuf Definitions

The protobuf definitions are in `node.proto`. To compile the definitions, run `protoc.sh` from this directory. This will generate several `node_pb*.py*` files. 

> NOTE: Unless you need to change the protobuf definitions, you don't need to run the protobuf compiler since the generated files are version-controlled.

## Example Server

The `server.py` module has an example server. You can run it with `python server.py`.

## Unit Tests

There are unit tests in `tests/test_grpc.py`. These start a server subprocess and then run node operations using the `GrpcNodeClientDriver`.

