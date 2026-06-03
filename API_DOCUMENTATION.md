# API Documentation - Booking Lapangan REST API

## Base URL
```
http://localhost:5000/api
```

## Authentication
Semua endpoint (kecuali `/auth/login` dan `/auth/register`) memerlukan JWT token di header:
```
Authorization: Bearer <your_jwt_token>
```

---

## AUTH ENDPOINTS

### 1. Login
**POST** `/auth/login`

Request:
```json
{
  "username": "admin",
  "password": "123"
}
```

Response (200):
```json
{
  "success": true,
  "message": "Login berhasil",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "username": "admin",
    "role": "admin"
  }
}
```

### 2. Register
**POST** `/auth/register`

Request:
```json
{
  "username": "newuser",
  "password": "password123"
}
```

Response (201):
```json
{
  "success": true,
  "message": "Registrasi berhasil"
}
```

### 3. Verify Token
**GET** `/auth/verify`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Token valid",
  "data": {
    "username": "admin",
    "role": "admin",
    "exp": 1234567890,
    "iat": 1234567800
  }
}
```

---

## LAPANGAN ENDPOINTS

### 1. Get Semua Lapangan
**GET** `/lapangan`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "nama_lapangan": "Lapangan A",
      "deskripsi": "Lapangan futsal",
      "created_at": "2024-01-15 10:30:00"
    }
  ]
}
```

### 2. Create Lapangan (Admin Only)
**POST** `/lapangan`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "nama_lapangan": "Lapangan B",
  "deskripsi": "Lapangan badminton"
}
```

Response (201):
```json
{
  "success": true,
  "message": "Lapangan berhasil ditambahkan",
  "data": {
    "id": 2,
    "nama_lapangan": "Lapangan B"
  }
}
```

### 3. Delete Lapangan (Admin Only)
**DELETE** `/lapangan/<id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Lapangan berhasil dihapus"
}
```

---

## BOOKING ENDPOINTS

### 1. Get Semua Booking
**GET** `/booking`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "nama_pemesan": "john",
      "nama_lapangan": "Lapangan A",
      "tanggal": "2024-06-10",
      "jam_mulai": "14:00:00",
      "jam_selesai": "15:00:00",
      "catatan": "Extra ball needed",
      "role_pemesan": "user",
      "status": "Menunggu Persetujuan",
      "created_at": "2024-06-03 10:30:00"
    }
  ]
}
```

**Note:** User role hanya melihat booking mereka sendiri, admin/pegawai/pengurus melihat semua.

### 2. Create Booking
**POST** `/booking`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "nama_lapangan": "Lapangan A",
  "tanggal": "2024-06-10",
  "jam_mulai": "14:00",
  "jam_selesai": "15:00",
  "catatan": "Extra ball needed"
}
```

Response (201):
```json
{
  "success": true,
  "message": "Booking berhasil disimpan dan menunggu persetujuan",
  "data": {
    "id": 1
  }
}
```

### 3. Get Booking Detail
**GET** `/booking/<id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "nama_pemesan": "john",
    "nama_lapangan": "Lapangan A",
    "tanggal": "2024-06-10",
    "jam_mulai": "14:00:00",
    "jam_selesai": "15:00:00",
    "catatan": "Extra ball needed",
    "role_pemesan": "user",
    "status": "Menunggu Persetujuan",
    "created_at": "2024-06-03 10:30:00"
  }
}
```

### 4. Update Booking Status (Admin/Pengurus Only)
**PUT** `/booking/<id>/status`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "action": "acc"
}
```

Valid actions: `acc`, `ditolak`, `selesai`, `batal`

Response (200):
```json
{
  "success": true,
  "message": "Status berhasil diubah menjadi Disetujui (ACC)"
}
```

### 5. Cancel Booking
**POST** `/booking/<id>/cancel`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Booking dibatalkan"
}
```

### 6. Delete Booking (Admin Only)
**DELETE** `/booking/<id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Booking berhasil dihapus"
}
```

---

## JADWAL ENDPOINTS

### 1. Get Jadwal per Tanggal
**GET** `/jadwal?tanggal=2024-06-10`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "tanggal": "2024-06-10",
    "lapangan": [
      {
        "lapangan": {
          "id": 1,
          "nama_lapangan": "Lapangan A",
          "deskripsi": "Lapangan futsal"
        },
        "status": "Terisi",
        "bookings": [
          {
            "id": 1,
            "jam_mulai": "14:00:00",
            "jam_selesai": "15:00:00",
            "status": "Disetujui (ACC)"
          }
        ]
      }
    ]
  }
}
```

---

## ADMIN ENDPOINTS

### 1. Get Semua Users (Admin Only)
**GET** `/admin/users`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [
    ["admin", {"password": "123", "role": "admin"}],
    ["john", {"password": "pass123", "role": "user"}]
  ]
}
```

### 2. Create User (Admin Only)
**POST** `/admin/users`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "username": "newpegawai",
  "password": "password123",
  "role": "pegawai"
}
```

Response (201):
```json
{
  "success": true,
  "message": "User newpegawai berhasil dibuat"
}
```

### 3. Delete User (Admin Only)
**DELETE** `/admin/users/<username>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "User john berhasil dihapus"
}
```

### 4. Get Laporan (Admin Only)
**GET** `/admin/laporan`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "total_booking": 25,
    "per_role": [
      {"role_pemesan": "user", "total": 15},
      {"role_pemesan": "pengurus", "total": 10}
    ],
    "per_lapangan": [
      {"nama_lapangan": "Lapangan A", "total": 12},
      {"nama_lapangan": "Lapangan B", "total": 13}
    ],
    "per_tanggal": [
      {"tanggal": "2024-06-10", "total": 3}
    ]
  }
}
```

---

## HEALTH CHECK

### Health Check
**GET** `/health`

Response (200):
```json
{
  "success": true,
  "message": "API berjalan normal",
  "timestamp": "2024-06-03T10:30:45.123456"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Field tidak lengkap"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Token tidak ditemukan"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "message": "Akses ditolak: role tidak sesuai"
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Endpoint tidak ditemukan"
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Lapangan sudah tidak tersedia pada jadwal tersebut"
}
```

---

## Implementation Notes

1. **JWT Token Expiry**: 7 hari (604800 detik)
2. **DateTime Format**: ISO 8601 (YYYY-MM-DDTHH:MM:SS)
3. **Role Hierarchy**: 
   - `admin`: Full access to all endpoints
   - `pengurus`: Can approve bookings
   - `pegawai`: Can view and manage
   - `user`: Can only manage own bookings
4. **CORS**: Configured to accept requests from mobile apps (localhost dan production URLs)

---

## Testing dengan cURL

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123"}'

# Get Lapangan (ganti TOKEN dengan actual token)
curl -X GET http://localhost:5000/api/lapangan \
  -H "Authorization: Bearer TOKEN"

# Create Booking
curl -X POST http://localhost:5000/api/booking \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nama_lapangan": "Lapangan A",
    "tanggal": "2024-06-10",
    "jam_mulai": "14:00",
    "jam_selesai": "15:00"
  }'
```
