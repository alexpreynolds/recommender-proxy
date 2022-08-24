#!/usr/bin/env node

/**
 * Simple proxy server to get around cross domain issues
 */

const express = require("express");
const https = require("https");
const fs = require("fs");
const debug = require("debug")("url-proxy:server");
const normalizePort = require("normalize-port");
const nocache = require("nocache");
const morgan = require("morgan");
const spawn = require("child_process").spawn;
const util = require("util");

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
 * v2 request 
 * tabix database lookup
 * 
 * GET https://localhost:9002/v2?datasetAltname=...&assembly=...&stateModel=...&groupEncoded=...&saliencyLevel=...&chromosome=...&start=...&end=...&tabixUrlEncoded=...&outputFormat=...
 *
 */

app.get("/v2", (req, res, next) => {
  let datasetAltname = req.query.datasetAltname; // new name scheme, e.g. vA, vC, dhsIndex, etc.
  let assembly = req.query.assembly;
  let stateModel = req.query.stateModel;
  let group = decodeURIComponent(req.query.groupEncoded); // new name scheme
  let saliencyLevel = req.query.saliencyLevel; // new name scheme
  let chromosome = req.query.chromosome;
  let start = parseInt(req.query.start);
  let end = parseInt(req.query.end);
  let tabixUrl = decodeURIComponent(req.query.tabixUrlEncoded);
  let scaleLevel = parseInt(req.query.scaleLevel);
  let windowSize = parseInt(req.query.windowSize);   
  let outputFormat = req.query.outputFormat;
  let queryRegionDiff = end - start;
  let windowSizeRawBases = windowSize * 1000;
  let hitPadding = parseInt(parseFloat(queryRegionDiff - windowSizeRawBases) / 2);
  let queryRegionDiffAsWindowSize = parseInt(parseFloat(queryRegionDiff) / 1000);
  /**
   * We use a temporary directory as a working directory, so 
   * that tbi index files are stored where they will be deleted,
   * presumably after some period of time, so that they do not
   * accumulate and fill up disk storage.
   *
   * It is also necessary to use the dataset name (or alternate name)
   * to specify a unique path for the tabix index. Otherwise, the
   * index file will be clobbered where two datasets share the same
   * assembly and state model (for example, Roadmap and Adsera datasets).
   * This will lead to queries failing or returning bogus results.
   */
  const tabixIndexTmpDir = (datasetAltname === 'dhsIndex') ? `/tmp/${datasetAltname}/${assembly}/${group}/${scaleLevel}/${windowSize}` : `/tmp/recommender/v2/${datasetAltname}/${assembly}/${stateModel}/${group}/${saliencyLevel}/${scaleLevel}/${windowSize}`;
  if (!fs.existsSync(tabixIndexTmpDir)) { fs.mkdirSync(tabixIndexTmpDir, { recursive: true }); }
  const tabixSpawnOptions = {
    "cwd"   : tabixIndexTmpDir,
    "shell" : true
  };
  //
  // e.g., tabix http://explore.altius.org/tabix/recommender/v2/vC/hg19/18/All_833_biosamples/S1/5/25/recommendations.bed.gz chr1:14004000-14004001
  //
  // const scaleLevel = 5;
  // const windowSize = 25;
  const tabixPath = (datasetAltname === 'dhsIndex') ? `${tabixUrl}/${datasetAltname}/${assembly}/${group}/${scaleLevel}/${windowSize}/recommendations.bed.gz` : `${tabixUrl}/recommender/v2/${datasetAltname}/${assembly}/${stateModel}/${group}/${saliencyLevel}/${scaleLevel}/${windowSize}/recommendations.bed.gz`;
  const midpoint = start + Math.abs(Math.floor((end - start) / 2));
  // const tabixRange = `${chromosome}:${midpoint}-${(midpoint+1)}`;
  const tabixRange = `${chromosome}:${start}-${end}`;
  const tabixCmdArgs = [tabixPath, tabixRange];
  const tabixCmd = spawn('/usr/bin/tabix', tabixCmdArgs, tabixSpawnOptions);
  let tabixData = '';
  tabixCmd.stdout.setEncoding('utf8');
  tabixCmd.stdout.on('data', function(data) {
    tabixData += data.toString();
  });
  tabixCmd.stdout.on('end', function() {
    switch (outputFormat) {
      case "BED": {
        res.set('Content-Type', 'text/plain');
        res.write(tabixData);
        break;
      }
      case "JSON": {
        // let processedTabixObject = { 
        //   "query": {
        //     "chromosome": chromosome,
        //     "start": start,
        //     "end": end,
        //     "midpoint": midpoint,
        //     "sizeKey": `${windowSize}k`, 
        //   },
        //   "hits":[] 
        // };
        let processedTabixObject = { 
          "query": {
            "chromosome": chromosome,
            "start": start,
            "end": end,
            "midpoint": midpoint,
            "sizeKey": `${queryRegionDiffAsWindowSize}k`,
            "windowSize": `${windowSize}k`,
            "tabixPath": `${tabixPath}`,
            "hitPadding": hitPadding,
            "hitCount": 0,
            "hitDistance": -1,
            "hitFirstInterval": [],
            "hitFirstStartDiff": -1,
            "hitFirstEndDiff": -1,
          },
          "hits":[] 
        };
        let tabixLines = tabixData.split('\n');
        const tabixLineCountZi = tabixLines.length - 2;
        processedTabixObject.query.hitCount = tabixLines.length - 1;
        let tabixLCZiMid = (tabixLineCountZi === 0) ? 0 : parseInt(tabixLineCountZi / 2);
        
        if (processedTabixObject.query.hitCount > 1) {
          // let intervals = [];
          const distances = [];
          tabixLines.forEach((r, i) => {
            // const tabixLineChr = parseInt(r.split('\t')[0]);
            const tabixLineStart = parseInt(r.split('\t')[1]);
            const tabixLineStop = parseInt(r.split('\t')[2]);
            if (tabixLineStart) {
              const tabixLineMid = tabixLineStart + parseInt(parseFloat(tabixLineStop - tabixLineStart) / 2.0);
              distances.push(Math.abs(tabixLineMid - midpoint));
              // intervals.push([tabixLineChr, tabixLineStart, tabixLineStop]);
            }
          });
          const minDistance = Math.min(...distances);
          const indexOfMinDistance = distances.indexOf(minDistance);
          // console.log(JSON.stringify(distances));
          // console.log(JSON.stringify(indexOfMinDistance));
          processedTabixObject.query.hitCount = 1;
          tabixLCZiMid = 0;
          tabixLines = [tabixLines[indexOfMinDistance]];
          processedTabixObject.query.hitDistance = minDistance;
          // processedTabixObject.query.hitDistances = distances;
          // processedTabixObject.query.hitIntervals = intervals;
        }
        // console.log(JSON.stringify(tabixLines));

        if (processedTabixObject.query.hitCount === 1) {
          tabixLines.forEach((r, i) => {
            if (r && i === tabixLCZiMid) {
              processedTabixObject.query.hitFirstInterval = r.split('\t').slice(0, 3);
              processedTabixObject.query.hitFirstStartDiff = processedTabixObject.query.hitFirstInterval[1] - start;
              processedTabixObject.query.hitFirstEndDiff = end - processedTabixObject.query.hitFirstInterval[2];
              const fields = r.split('\t')[3];
              let tabixHits = null;
              try {
                tabixHits = JSON.parse(fields);
                tabixHits.forEach((hv, hi) => {
                  let tabixHitElements = hv.split(':');
                  tabixHitElements[1] = parseInt(tabixHitElements[1]) - processedTabixObject.query.hitFirstStartDiff;
                  tabixHitElements[2] = parseInt(tabixHitElements[2]) + processedTabixObject.query.hitFirstEndDiff;
                  tabixHits[hi] = tabixHitElements.join(':');
                });
              }
              catch (err) {
                tabixHits = JSON.parse(fields.replace('"[', '[').replace(']"', ']').replace(/""/g, '"'));
                // console.log(`tabixHits post-replace | ${tabixHits.length} | ${tabixHits}`);
              }
              const firstHit = tabixHits[0].split(':');
              // processedTabixObject.query.chromosome = firstHit[0];
              // processedTabixObject.query.start = parseInt(firstHit[1]) - hitPadding;
              // processedTabixObject.query.end = parseInt(firstHit[2]) + hitPadding;
              // processedTabixObject.query.chromosome = chromosome;
              // processedTabixObject.query.start = start;
              // processedTabixObject.query.end = end;
              processedTabixObject.query.midpoint = processedTabixObject.query.start + Math.abs(Math.floor((processedTabixObject.query.end - processedTabixObject.query.start) / 2));
              // processedTabixObject.tabixHits.push(tabixHits.slice(1).join('\n').replace(/:/g, '\t'));
              let postPaddedHits = tabixHits.slice(1).join('\n').replace(/:/g, '\t');
              processedTabixObject.hits.push(postPaddedHits);
            }
          });
        }
        res.set('Content-Type', 'application/json');
        res.write(JSON.stringify(processedTabixObject));
        break;
      }  
      default: {
        res.status(400).send(`Invalid output format specified (${outputFormat})`);
        break;
      }
    }
  });
  tabixCmd.on('close', (tabixCmdExitCode) => {
    if (tabixCmdExitCode !== 0) {
      // console.log(`${tabixCmdExitCode} ${tabixCmd.spawnargs.join(' ')}`);
      req.pipe(tabixCmd.stdout).pipe(res);
    }
    else {
      req
        .pipe(tabixCmd.stdout)
        .on('response', function(response) {
          let contentLength = req.socket.bytesRead;
          if (contentLength > byteLimit) {
            res.status(400).send("Went over content byte limit");
          }
        })
        .pipe(res);
    }
    return;
  });
})

/**
 * v1 request 
 * matrix/cube lookup
 * 
 * GET https://localhost:9002/v1?datasetEncoded=...&datasetAltname=...&assembly=...&stateModel=...&groupEncoded=...&groupAltname=...&saliencyLevel=...&saliencyLevelAltname=...&chromosome=...&start=...&end=...&tabixSource=...&tabixUrlEncoded=...&databaseUrlEncoded=...&outputDestination=...&outputFormat=...
 *
 */

app.get("/v1", (req, res, next) => {
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
  let outputFormat = req.query.outputFormat;
  /**
   * We use a temporary directory as a working directory, so 
   * that tbi index files are stored where they will be deleted,
   * presumably after some period of time, so that they do not
   * accumulate and fill up disk storage.
   *
   * It is also necessary to use the dataset name (or alternate name)
   * to specify a unique path for the tabix index. Otherwise, the
   * index file will be clobbered where two datasets share the same
   * assembly and state model (for example, Roadmap and Adsera datasets).
   * This will lead to queries failing or returning bogus results.
   */
  let tmpDir = `/tmp/recommender/v1/${datasetAltname}`;
  if (!fs.existsSync(tmpDir)) { fs.mkdirSync(tmpDir, { recursive: true }); }
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
    "--output-destination", outputDestination,
    "--output-format", outputFormat
  ];
  let pyCmd = spawn("/home/ubuntu/recommender-proxy/recommender.py", pyArgs, spawnOptions);
  let pyData = "";
  let pyError = "";
  pyCmd.stdin.end();
  pyCmd.stdout.on("data", function(data) { pyData += data.toString(); });
  pyCmd.stdout.on("end", function() { res.write(pyData) } );
  pyCmd.stderr.on("data", function(data) { pyError += data.toString(); });
  pyCmd.on("close", (pyCmdExitCode) => {
    // check if recommender script exited with a non-zero error
    if ((pyCmdExitCode !== 0) || (pyCmd.stdout.length === 0)) {
      console.error(pyError);
      req.pipe(res);
    }
    else if ((outputFormat !== "JSON") && (outputFormat !== "BED")) {
      res.status(400).send(`Invalid output format specified (${outputFormat})`);
    }
    else {
      // Pipe the recommender result to the requesting client, if under the byte limit
      req
        .pipe(pyCmd.stdout)
        .on("response", function(response) {
          let contentLength = req.socket.bytesRead;
          if (contentLength > byteLimit) {
            res.status(400).send("Went over content byte limit");
          }
          /* Manually set content type */
          response.headers["content-type"] = (outputFormat === "JSON") ? "application/json" : (outputFormat === "BED") ? "text/plain" : "application/octet-stream";
        })
        .pipe(res);
    }
  });
});
