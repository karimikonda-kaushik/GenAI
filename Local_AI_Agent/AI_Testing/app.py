import ast
import math
import operator
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Calculation history in-memory (stores up to 50 items)
history = []
MAX_HISTORY = 50

# Supported binary operators
BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Supported constants and functions
ALLOWED_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    "fact": math.factorial,
}


class SafeEvalVisitor(ast.NodeVisitor):
    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    # For Python < 3.8 compatibility
    def visit_Num(self, node):
        return node.n

    def visit_BinOp(self, node):
        op_type = type(node.op)
        if op_type not in BINARY_OPS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)

        if op_type == ast.Div and right == 0:
            raise ZeroDivisionError("Division by zero")
        if op_type == ast.FloorDiv and right == 0:
            raise ZeroDivisionError("Division by zero")
        if op_type == ast.Mod and right == 0:
            raise ZeroDivisionError("Modulo by zero")
        if op_type == ast.Pow and left == 0 and right < 0:
            raise ZeroDivisionError("Zero to negative power")

        # Limit exponent size to prevent CPU exhaustion
        if op_type == ast.Pow and abs(right) > 1000:
            raise ValueError("Exponent too large")

        return BINARY_OPS[op_type](left, right)

    def visit_UnaryOp(self, node):
        op_type = type(node.op)
        if op_type not in UNARY_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return UNARY_OPS[op_type](operand)

    def visit_Name(self, node):
        if node.id in ALLOWED_NAMES and isinstance(ALLOWED_NAMES[node.id], (int, float)):
            return ALLOWED_NAMES[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Invalid function call")
        func_name = node.func.id
        if func_name not in ALLOWED_NAMES or not callable(ALLOWED_NAMES[func_name]):
            raise ValueError(f"Unsupported function: {func_name}")

        args = [self.visit(arg) for arg in node.args]
        return ALLOWED_NAMES[func_name](*args)


def safe_evaluate(expression: str):
    """Safely parse and evaluate mathematical expressions."""
    if not expression or not expression.strip():
        raise ValueError("Expression is empty")

    expr = expression.strip()
    # Normalize common symbols
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")

    # Safety check on length
    if len(expr) > 200:
        raise ValueError("Expression too long")

    try:
        parsed = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e.msg}")

    visitor = SafeEvalVisitor()
    result = visitor.visit(parsed)

    # Format result: convert whole float numbers to int for clean display
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    elif isinstance(result, float):
        result = round(result, 10)

    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    raw_expression = data.get("expression", "")

    if not raw_expression:
        return jsonify({"success": False, "error": "No expression provided"}), 400

    try:
        result = safe_evaluate(raw_expression)
        item = {
            "expression": raw_expression,
            "result": str(result),
        }
        history.insert(0, item)
        if len(history) > MAX_HISTORY:
            history.pop()

        return jsonify({"success": True, "expression": raw_expression, "result": result})
    except ZeroDivisionError:
        return jsonify({"success": False, "error": "Cannot divide by zero"}), 400
    except OverflowError:
        return jsonify({"success": False, "error": "Numerical overflow"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify({"success": True, "history": history})


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    history.clear()
    return jsonify({"success": True, "message": "History cleared"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
