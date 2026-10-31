from pydantic import BaseModel, Field


class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=15)


class OtpRequestOut(BaseModel):
    sent: bool = True
    dev_otp: str | None = None


class OtpVerify(BaseModel):
    phone: str = Field(min_length=10, max_length=15)
    otp: str = Field(min_length=4, max_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
