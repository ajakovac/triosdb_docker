from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from api.dependencies import get_session
from src.session.manager import SessionManager
from src.database.client import DataClient
from src.utils.file_to_data_hierarchical import list_to_data_hierarchical
from api.models.response_model import APIResponse
import pandas as pd
import io
import json

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/upload")
async def upload_command(
    file: UploadFile = File(...),
    module: str = Form(...),  # ✅ also accept the 'module' input
    token: str = Depends(oauth2_scheme),
    session: SessionManager = Depends(get_session)):

    try:
        user = session.get_user_by_token(token)
        data_client = session.login_data[user]
    except:
        return APIResponse(
            command= f'upload into module {module}',
            message= "invalid token",
        )
    permitted = data_client.simple_get([user],['write'],['*']).format('value')
    if '_all' not in permitted and module not in permitted:
        return APIResponse(
            command= f'upload into module {module}',
            timestamp=cmd_response.timestamp,
            message= f'You are not allowed to load into module "{module}"',
            success=False,
            output= None
        )
    filename = file.filename.lower()

    # Read file contents as bytes
    contents = await file.read()

    filetype = None
    try:
        # Decide how to parse based on file extension
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contents))
            filetype = "table"
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
            filetype = "table"
        elif filename.endswith(".txt"):
            lines = contents.decode("utf-8").splitlines()
            # Example: parse lines into a DataFrame
            list_to_data_hierarchical(data_client, module, lines)
        elif filename.endswith(".json"):
            data = json.loads(contents.decode("utf-8"))
            data_client.load_from_json(data, module)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

    if filetype == "table":
        headers = df.columns.tolist()
        data = df.values.tolist()
        for d in data:
            name = d.pop(0)
            for i,v in enumerate(d):
                if not pd.isna(v):
                    data_client.new(name, module)
                    data_client.set(f'{name}:{headers[i+1]}:{v}')

    cmd_response = session.command(module, token=token)
    return APIResponse(
        command=cmd_response.command,
        timestamp=cmd_response.timestamp,
        message=cmd_response.message,
        success=cmd_response.success,
        output= None if cmd_response.output is None else cmd_response.output.show()
    )


