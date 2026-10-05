from pydantic import BaseModel


class CodeProblem(BaseModel):
    title: str
    description: str


class CodeSolution(BaseModel):
    title: str
    description: str
    code: str
    img_path: str | None = None
