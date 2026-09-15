from app.graph.workflow import generate_plan


def generate(req, pantry):
    result = generate_plan(req.model_dump(), pantry)
    return result["meals"], result["errors"]
