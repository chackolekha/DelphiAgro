import enum


class Role(enum.StrEnum):
    FARMER = "FARMER"
    RETAILER = "RETAILER"
    ADMIN = "ADMIN"


class UserStatus(enum.StrEnum):
    REGISTERED = "REGISTERED"
    KYC_SUBMITTED = "KYC_SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class KycMethod(enum.StrEnum):
    DIGILOCKER = "DIGILOCKER"
    OFFLINE_XML = "OFFLINE_XML"
    OTP_EKYC = "OTP_EKYC"
    MANUAL_DOC = "MANUAL_DOC"


class ReviewStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PayoutType(enum.StrEnum):
    BANK = "BANK"
    UPI = "UPI"


class ListingUnit(enum.StrEnum):
    KG = "KG"
    QUINTAL = "QUINTAL"
    CRATE = "CRATE"


class OrderStatus(enum.StrEnum):
    PLACED = "PLACED"
    PAID = "PAID"
    ACCEPTED = "ACCEPTED"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    DISPUTED = "DISPUTED"
    SETTLED = "SETTLED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaymentType(enum.StrEnum):
    CAPTURE = "CAPTURE"
    REFUND = "REFUND"
    TRANSFER = "TRANSFER"


class PaymentStatus(enum.StrEnum):
    CREATED = "CREATED"
    CAPTURED = "CAPTURED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DisputeResolution(enum.StrEnum):
    RELEASE = "RELEASE"
    REFUND = "REFUND"


class DisputeStatus(enum.StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
