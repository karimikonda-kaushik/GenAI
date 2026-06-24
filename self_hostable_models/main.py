from crypt import methods
from re import L
from langchain.chat_models import init_chat_model
import flask
from flask import Flask, request, jsonify

app = Flask(__name__)



model = init_chat_model(
    model='llama3.2:1b',
    model_provider="ollama"
)


#this part is used to get the data from the client and send it to the model
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    print(data)
    response =model.invoke(data['messages'])
    return jsonify(
        {"message": {"role": "assistant",
        "content": response.content}}
        )

#response = model.invoke("Can I become AI Engineer in one year?")
#print(response.content)

if __name__ == "__main__":
    app.run(debug=True, port=5002)