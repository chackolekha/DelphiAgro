export type Role = "FARMER" | "RETAILER" | "ADMIN";
export type UserStatus =
  | "REGISTERED"
  | "KYC_SUBMITTED"
  | "VERIFIED"
  | "REJECTED"
  | "SUSPENDED";
export type OrderStatus =
  | "PLACED" | "PAID" | "ACCEPTED" | "PACKED" | "DISPATCHED"
  | "DELIVERED" | "DISPUTED" | "SETTLED" | "REFUNDED" | "CANCELLED" | "REJECTED";

export interface User {
  id: string;
  phone: string;
  role: Role | null;
  status: UserStatus;
  name: string | null;
  district: string | null;
  state: string | null;
  pincode: string | null;
  gstin: string | null;
}

export interface Listing {
  id: string;
  farmer_id: string;
  category: string;
  variety: string | null;
  grade: string | null;
  unit: "KG" | "QUINTAL" | "CRATE";
  price_per_unit: string;
  qty_available: string;
  min_order_qty: string;
  district: string | null;
  pickup_location: string | null;
  harvest_date: string | null;
  active: boolean;
  created_at: string;
}

export interface Order {
  id: string;
  retailer_id: string;
  farmer_id: string;
  status: OrderStatus;
  total_amount: string;
  platform_fee: string;
  accept_by: string | null;
  vehicle_no: string | null;
  driver_phone: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface OrderItem {
  id: string;
  listing_id: string;
  quantity: string;
  price_per_unit: string;
  line_total: string;
  category: string | null;
  unit: string | null;
}

export interface OrderEvent {
  id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  actor_role: string | null;
  note: string | null;
  created_at: string;
}

export interface Payment {
  id: string;
  type: "CAPTURE" | "REFUND" | "TRANSFER";
  status: string;
  amount: string;
  created_at: string;
}

export interface OrderDetail {
  order: Order;
  items: OrderItem[];
  events: OrderEvent[];
  payments: Payment[];
  delivery_otp: string | null;
}

export interface KycQueueItem {
  id: string;
  user_id: string;
  user_name: string | null;
  user_phone: string;
  user_role: string | null;
  method: string;
  kyc_name: string | null;
  kyc_dob: string | null;
  aadhaar_last4: string | null;
  review_status: string;
  created_at: string;
}

export interface Dispute {
  id: string;
  order_id: string;
  raised_by: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}
