import datetime
import redis
import pickle
import uuid
from queue import Queue
from flask import Flask, jsonify, make_response, request
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(process)d - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__file__)

QUEUE_SIZE = 32

q = Queue()
r = redis.Redis(host="localhost", port=6379, db=0)

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    logger = app.logger
    start = datetime.datetime.now()
    body = request.json
    logger.debug(f"Received request: {body}")

    qsize = q.qsize()
    logger.info(f"Queue size: {qsize}")

    if qsize >= QUEUE_SIZE:
        logger.warning("Queue is full, try again later")
        return make_response({"error": "Queue full , try again later"}, 503)

    if "inputs" not in body:
        logger.error("Missing `inputs` field")
        return make_response({"error": "`inputs` is required"}, 400)

    inputs = body.get("inputs", "Hello")
    parameters = body.get("parameters", {})

    # Validate parameters
    temperature = parameters.get("temperature", None)
    if temperature is not None:
        if not isinstance(temperature, (int, float)) or temperature <= 0:
            logger.error(f"Invalid temperature value: {temperature}")
            return make_response({"error": "Temperature needs to be >0"}, 400)
        temperature = float(temperature)

    top_k = parameters.get("top_k", None)
    if top_k is not None:
        if not isinstance(top_k, (int)) or top_k <= 0:
            logger.error(f"Invalid top_k value: {top_k}")
            return make_response({"error": "top_k is an integer > 0"}, 400)
        top_k = int(top_k)

    top_p = parameters.get("top_p", None)
    if top_p is not None:
        if not isinstance(top_p, (int, float)) or top_p <= 0 or top_p > 1:
            logger.error(f"Invalid top_p value: {top_p}")
            return make_response({"error": "top_p is a float > 0 and <=1"}, 400)
        top_p = float(top_p)

    parameters = {
        "do_sample": parameters.get("do_sample", None),
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "max_new_tokens": parameters.get("max_new_tokens", 20),
    }

    # Check max_new_tokens constraint
    if parameters["max_new_tokens"] > 512:
        logger.error("max_new_tokens exceeded limit")
        return make_response(
            {"error": "You cannot generate more than 512 new tokens"},
            400,
        )

    topic = str(uuid.uuid4()).encode("utf-8")
    p = r.pubsub()
    p.subscribe([topic])

    q.put(1)
    r.publish("query", pickle.dumps((topic, inputs, parameters)))

    for message in p.listen():
        if message["type"] == "message":
            q.get()
            out = pickle.loads(message["data"])
            if "error" in out:
                logger.error(f"Error in processing message: {out['error']}")
                return make_response(out, 400)
            elapsed = datetime.datetime.now() - start
            logger.info(f"Generated output: {out['output']}")
            logger.info(f"Elapsed time: {elapsed}")
            return make_response(jsonify([{"generated_text": out["output"]}]), 200)


if __name__ == "__main__":
    app.run("127.0.0.1", port=8000)
