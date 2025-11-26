from fastapi import FastAPI, HTTPException, Depends, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import os
from dotenv import load_dotenv

# 确保在项目根目录加载.env文件
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from database import engine, Base, get_db
from models import User, AIConversation, AIMessage, AIFile, PasswordResetToken
from auth import get_current_user



# 创建数据库表
Base.metadata.create_all(bind=engine)

# Pydantic模型
class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None
    avatar: str | None = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str = None
    role: str
    created_at: datetime

class ForgotPasswordRequest(BaseModel):
    username: str
    email: EmailStr
    
    @validator('email')
    def validate_qq_email(cls, v):
        if '@qq.com' in str(v).lower():
            # QQ邮箱验证：确保格式正确
            local_part = str(v).split('@')[0]
            if not local_part or len(local_part) < 5 or len(local_part) > 20:
                raise ValueError('QQ邮箱格式不正确')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser",
                "email": "12345678@qq.com"
            }
        }

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class GetPasswordRequest(BaseModel):
    username: str

class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

# FastAPI应用
app = FastAPI(title="基于SDN的流量检测与监控系统API", version="1.0.0")

# CORS配置 - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173", 
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:5176", "http://127.0.0.1:5176"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 导入AI路由
# AI路由已移除，使用Ollama替代

# API路由前缀
API_PREFIX = "/api"

# 用户头像API
@app.get(f"{API_PREFIX}/auth/user-avatar/{{username}}")
def get_user_avatar(username: str, db: Session = Depends(get_db)):
    """获取用户头像"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"success": False, "message": "用户不存在"}
    
    return {"success": True, "avatar": user.avatar}

# 用户登录API
@app.post(f"{API_PREFIX}/auth/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_login.username).first()
    if not user or user.hashed_password != user_login.password:
        return {"success": False, "message": "用户名或密码错误"}

    # 返回用户信息和token（这里简化处理，使用用户ID作为token）
    return {
        "success": True,
        "message": "登录成功",
        "token": str(user.id),
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role or "admin",
            "avatar": user.avatar,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }

# 导入SDN路由（已迁移到v1_routes.py，不再需要单独的sdn_router）
# from sdn_routes import sdn_router
# app.include_router(sdn_router)

# 导入黑白名单路由
from blacklist_routes import router as blacklist_router
app.include_router(blacklist_router)

# 导入Ollama路由
from ollama_routes import router as ollama_router
app.include_router(ollama_router)

# 导入V1路由
from v1_routes import router as v1_router
# 同时支持/api/v1和/v1两种路径格式
app.include_router(v1_router, prefix="/api")
app.include_router(v1_router)

# 导入Agent路由（RAG + MCP + Agent）
try:
    from agent_routes import router as agent_router
    app.include_router(agent_router)
    print("✅ Agent路由已加载")
except Exception as e:
    print(f"⚠️ Agent路由加载失败: {e}")



# API路由
@app.get("/")
async def root():
    return {"message": "基于SDN的流量检测与监控系统API服务已启动"}

@app.post("/api/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # 输入验证
        if not user.username or len(user.username.strip()) < 3:
            raise HTTPException(status_code=400, detail="用户名长度不能少于3个字符")
        
        if not user.password or len(user.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于6个字符")
        
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user.username.strip()).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建新用户
        new_user = User(
            username=user.username.strip(),
            hashed_password=user.password,  # 生产环境应使用哈希
            email=user.email.strip() if user.email else None,
            role="admin",
            avatar=user.avatar if user.avatar and user.avatar.strip() else None
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "注册成功",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role,
                "avatar": new_user.avatar
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"注册错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试")



@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": [{
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
        "created_at": user.created_at
    } for user in users]}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "avatar": current_user.avatar,
            "created_at": current_user.created_at
        }
    }

@app.get("/api/auth/user-avatar/{username}")
async def get_user_avatar(username: str, db: Session = Depends(get_db)):
    """根据用户名获取用户头像（无需认证）"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"avatar": None}
    
    return {
        "success": True,
        "avatar": user.avatar
    }

@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 检查用户名是否存在
    user_by_username = db.query(User).filter(User.username == request.username).first()
    if not user_by_username:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查邮箱是否匹配
    user = db.query(User).filter(
        User.username == request.username,
        User.email == request.email
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="邮箱不匹配")
    
    # 生成重置token
    reset_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=30)  # 30分钟后过期

    # 保存token到数据库
    reset_entry = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    )
    
    db.add(reset_entry)
    db.commit()
    
    # 在实际环境中，这里应该发送邮件
    # 为了演示，我们返回token
    return {
        "success": True,
        "message": "重置邮件已发送",
        "reset_token": reset_token,  # 演示用，实际应该通过邮件发送
        "expires_at": expires_at.isoformat()
    }

@app.post("/api/auth/verify-reset-token")
async def verify_reset_token(token: str, db: Session = Depends(get_db)):
    # 查找有效的token
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used == False
    ).first()
    
    if not reset_entry:
        raise HTTPException(status_code=400, detail="无效的或已过期的重置链接")
    
    return {
        "success": True,
        "message": "重置链接有效",
        "user_id": reset_entry.user_id
    }

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # 查找有效的token
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used == False
    ).first()
    
    if not reset_entry:
        raise HTTPException(status_code=400, detail="无效的或已过期的重置链接")
    
    # 更新用户密码
    user = db.query(User).filter(User.id == reset_entry.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.hashed_password = request.new_password  # 生产环境应使用哈希
    reset_entry.used = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "密码重置成功"
    }

@app.post("/api/auth/get-password")
async def get_password(request: GetPasswordRequest, db: Session = Depends(get_db)):
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "message": "密码获取成功",
        "password": user.hashed_password  # 注意：生产环境不应该返回明文密码
    }

@app.post("/api/auth/change-password")
async def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    # 检查用户是否存在
    user_check = db.query(User).filter(User.username == request.username).first()
    if not user_check:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 验证密码
    user = db.query(User).filter(
        User.username == request.username,
        User.hashed_password == request.old_password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="原密码错误")
    
    # 更新用户密码
    user.hashed_password = request.new_password  # 生产环境应使用哈希
    db.commit()
    
    return {
        "success": True,
        "message": "密码修改成功"
    }

@app.post("/api/auth/update-avatar")
async def update_avatar(
    username: str = Form(...),
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """更新用户头像"""
    # 检查用户是否存在
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证文件类型
    if not avatar.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    # 读取文件内容
    contents = await avatar.read()
    
    # 检查文件大小 (2MB)
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过2MB")
    
    # 将图片转换为base64
    import base64
    avatar_base64 = base64.b64encode(contents).decode('utf-8')
    
    # 更新用户头像
    user.avatar = f"data:{avatar.content_type};base64,{avatar_base64}"
    db.commit()
    
    return {
        "success": True,
        "message": "头像更新成功",
        "avatar_url": user.avatar
    }

@app.get("/api/auth/user-avatar/{username}")
async def get_user_avatar(username: str, db: Session = Depends(get_db)):
    """获取用户头像"""
    # 检查用户是否存在
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {
            "success": False,
            "message": "用户不存在",
            "avatar": None
        }
    
    return {
        "success": True,
        "message": "获取头像成功",
        "avatar": user.avatar
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)