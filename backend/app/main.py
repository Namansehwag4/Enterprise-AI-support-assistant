from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import auth, documents
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    DomainException,
    EntityNotFoundError,
    EntityAlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    InvalidOperationError
)
from app.infrastructure.db.session import engine
from app.infrastructure.db.models import Base

# Setup structured logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"])

# Domain Exception Handlers (translating domain errors to HTTP errors)
@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message}
    )

@app.exception_handler(EntityAlreadyExistsError)
async def entity_already_exists_handler(request: Request, exc: EntityAlreadyExistsError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message}
    )

@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"}
    )

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message}
    )

@app.exception_handler(InvalidOperationError)
async def invalid_operation_handler(request: Request, exc: InvalidOperationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message}
    )

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal system error occurred."}
    )

# Startup DB initialisation
@app.on_event("startup")
async def on_startup():
    # Automatically initialize tables in database for local convenience
    async with engine.begin() as conn:
        # Runs sync operations inside async connection runner
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["health"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}
