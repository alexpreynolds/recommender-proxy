#!/usr/bin/env node

/**
 * Simple proxy server to get around cross domain issues
 */

const express = require("express");
const request = require("request").defaults({ strictSSL: true });
const https = require("https");
const fs = require("fs");
const debug = require("debug")("url-proxy:server");
const normalizePort = require("normalize-port");
const nocache = require("nocache");
const morgan = require("morgan");
const validator = require("validator");
const spawn = require("child_process").spawn;

const app = module.exports = express();

/**
 * Listen
 */

let port = normalizePort(process.env.PORT || "9002");
app.set("port", port);

let byteLimit = (process.env.BYTELIMIT || 1024*1024);
// let lineLimit = (process.env.LINELIMIT || 100);

let privateKeyFn = (process.env.SSLPRIVATEKEY || "/etc/ssl/private/altius.org.key");
let certificateFn = (process.env.SSLCERTIFICATE || "/etc/ssl/certs/altius-bundle.crt");

let privateKey = fs.readFileSync(privateKeyFn);
let certificate = fs.readFileSync(certificateFn);

const options = {
  key: privateKey,
  cert: certificate
};

let server = https.createServer(options, app);
server.listen(port);
server.on("error", onError);
server.on("listening", onListening);

/**
 * Event listener for HTTP server "error" event.
 */

function onError(error) {
  if (error.syscall !== "listen") {
    throw error;
  }

  let bind = typeof port === "string"
    ? "Pipe " + port
    : "Port " + port;

  // handle specific listen errors with friendly messages
  switch (error.code) {
    case "EACCES":
      console.error(bind + " requires elevated privileges");
      process.exit(1);
      break;
    case "EADDRINUSE":
      console.error(bind + " is already in use");
      process.exit(1);
      break;
    default:
      throw error;
  }
}

/**
 * Event listener for HTTP server "listening" event.
 */

function onListening() {
  let addr = server.address();
  let bind = typeof addr === "string"
    ? "pipe " + addr
    : "port " + addr.port;
  debug("Listening on " + bind);
}

/**
 * Allow CORS
 */

function cors(req, res, next) {
  res.set("Access-Control-Allow-Origin", req.headers.origin);
  res.set("Access-Control-Allow-Methods", req.method);
  res.set("Access-Control-Allow-Headers", "X-Requested-With, Content-Type");
  res.set("Access-Control-Allow-Credentials", true);

  // Respond OK if the method is OPTIONS
  if (req.method === "OPTIONS") {
    return res.send(200);
  } else {
    return next();
  }
}

/**
 * Response, CORS, cache policy and logging
 */

app.use(cors);
app.use(nocache());
app.use(morgan("combined"));

app.get("/favicon.ico", (req, res) => {
  res.sendStatus(404);
});

/**
 *
 * GET https://localhost:9002/?datasetEncoded=...&datasetAltname=...&assembly=...&stateModel=...&groupEncoded=...&groupAltname=...&saliencyLevel=...&saliencyLevelAltname=...&chromosome=...&start=...&end=...&tabixSource=...&tabixUrlEncoded=...&databaseUrlEncoded=...&outputDestination=...
 *
 */

app.get("/", (req, res, next) => {
  let dataset = decodeURIComponent(req.query.datasetEncoded);
  let datasetAltname = req.query.datasetAltname;
  let assembly = req.query.assembly;
  let stateModel = req.query.stateModel;
  let group = decodeURIComponent(req.query.groupEncoded); // new name scheme
  let groupAltname = req.query.groupAltname; // old name scheme
  let saliencyLevel = req.query.saliencyLevel; // new name scheme
  let saliencyLevelAltname = req.query.saliencyLevelAltname; // old name scheme
  let chromosome = req.query.chromosome;
  let start = req.query.start;
  let end = req.query.end;
  let tabixSource = req.query.tabixSource;
  let tabixUrl = decodeURIComponent(req.query.tabixUrlEncoded);
  let databaseUrl = decodeURIComponent(req.query.databaseUrlEncoded);
  let outputDestination = req.query.outputDestination;
  /**
   * We use a temporary directory as a working directory, so 
   * that tbi index files are stored where they will be deleted,
   * presumably after some period of time, so that they do not
   * accumulate and fill up disk storage.
   */
  let tmpDir = "/tmp/recommender";
  if (!fs.existsSync(tmpDir)) { fs.mkdirSync(tmpDir); }
  let spawnOptions = {
    "cwd"   : tmpDir,
    "shell" : true
  };
  /**
   * Python job options
   */
  let pyArgs = [
    "--dataset", dataset,
    "--dataset-altname", datasetAltname,
    "--assembly", assembly,
    "--state-model", stateModel,
    "--group", group,
    "--group-altname", groupAltname,
    "--saliency-level", saliencyLevel,
    "--saliency-level-altname", saliencyLevelAltname,
    "--chromosome", chromosome,
    "--start", start, 
    "--end", end,
    "--tabix-source", tabixSource,
    "--tabix-url", tabixUrl,
    "--database-url", databaseUrl,
    "--output-destination", outputDestination
  ];
  let pyCmd = spawn("/home/ubuntu/recommender-proxy/recommender.py", pyArgs, spawnOptions);
  let pyData = "";
  pyCmd.stdin.end();
  pyCmd.stdout.on("data", function(data) { pyData += data.toString(); });
  pyCmd.stdout.on("end", function() { res.write(pyData) } );
  pyCmd.on("close", (pyCmdExitCode) => {
    // check if recommender script exited with a non-zero error
    if (pyCmdExitCode !== 0) {
      console.log(`${pyCmdExitCode}`);
      console.log(`${JSON.stringify(pyCmd.stderr)}`);
      res.status(400).send(`Invalid input or other error (${pyCmdExitCode})`);
    }
    else {
      // pipe the recommender result to the requesting client, if under the byte limit
      req
        .pipe(pyCmd.stdout)
        .on("response", function(response) {
          let contentLength = req.socket.bytesRead;
          if (contentLength > byteLimit) {
            res.status(400).send("Went over content byte limit");
          }
          /* Rewrite content header to force it to text */
          response.headers["content-type"] = "text/plain";
        })
        .pipe(res);
    }
  });
});
