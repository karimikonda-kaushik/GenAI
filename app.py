import os
import uuid

from flask import Flask, redirect, render_template, request, session, url_for
from langchain_core.messages import HumanMessage

from weatherwebapp import agent

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


def get_config():
    if "thread_id" not in session:
        session["thread_id"] = str(uuid.uuid4())
    return {"configurable": {"thread_id": session["thread_id"]}}


def init_messages():
    if "messages" not in session:
        session["messages"] = []


@app.route("/")
def home():
    init_messages()
    return render_template("Chat.html", messages=session["messages"])


@app.route("/send", methods=["POST"])
def send():
    init_messages()
    user_message = request.form.get("message", "").strip()
    user_lat = request.form.get('latitude')
    user_lon = request.form.get('longitude')
    print(user_lat, user_lon)

    if user_lat and user_lon:
        session['user_location'] = {'lat': user_lat, 'lon': user_lon}

    if not user_message:
        return redirect(url_for("home"))

    response = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        get_config(),
    )

    session["messages"].append({"type": "human", "content": user_message})
    session["messages"].append(
        {"type": "ai", "content": response["messages"][-1].content}
    )
    session.modified = True
    return redirect(url_for("home"))


@app.route("/clear")
def clear():
    session.pop("thread_id", None)
    session.pop("messages", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
