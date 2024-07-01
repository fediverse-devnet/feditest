# Only linux-like support for now

cd ../../..
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. feditest/nodedrivers/grpc/node.proto