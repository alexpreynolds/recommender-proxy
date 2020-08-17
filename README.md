# recommender-proxy

A web backend to Nalu Tripician's pattern matching and retrieval tool

## Setup

Use the `recommender-proxy.development.json` file with PM2 to set up a web application. Valid SSL certificates are required. Root access to PM2 may be required if file permissions on SSL certs require it.

## Testing

There are two ways to test things out. The first is to run the recommender script directly on the host. If this works, the second test ensures that the web application server is running correctly.

### Python script

To test the Python script:

```console
$ ./test_request_via_python.sh
...
```

Adjust settings in the test script to test different parameters.

### Web request

To test the expressjs web application that calls the Python script:

```console
$ ./test_request_via_curl.sh
...
```

Both scripts should write results to standard output.