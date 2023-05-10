from flask import Flask, request
import redis
from .serialize import serialize, deserialize

app = Flask(__name__)

@app.route('/register_function', methods=['POST'])
def register_function():

@app.route('/execute_function', methods=['POST'])
def execute_function():

@app.route('/status/<int:task_id>', methods=['POST'])
def status(task_id):

@app.route('/result/<int:task_id>', methods=['POST'])
def result(task_id):

