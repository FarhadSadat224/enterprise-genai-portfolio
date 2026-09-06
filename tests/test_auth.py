import time
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_jwt_permissions_and_tenants():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    settings = Settings(_env_file=None, auth_mode="jwt", jwt_public_key=public, jwt_issuer="test")

    def headers(tenant, role="reader", exp=None):
        token = jwt.encode(
            {
                "sub": "user",
                "tenant": tenant,
                "role": role,
                "iss": "test",
                "aud": "portfolio",
                "iat": int(time.time()),
                "exp": exp or int(time.time()) + 60,
            },
            key,
            algorithm="RS256",
        )
        return {"Authorization": "Bearer " + token}

    with TestClient(create_app(settings)) as c:
        assert c.post("/chat", json={"message": "hello"}).status_code == 401
        assert (
            c.post("/chat", json={"message": "hello"}, headers=headers("a", exp=1)).status_code
            == 401
        )
        doc = {"source": "private.txt", "text": "zebra private evidence"}
        assert c.post("/documents", json=doc, headers=headers("a")).status_code == 403
        assert c.post("/documents", json=doc, headers=headers("a", "admin")).status_code == 201
        assert c.post("/chat", json={"message": "zebra"}, headers=headers("a")).json()["citations"]
        assert not c.post("/chat", json={"message": "zebra"}, headers=headers("b")).json()[
            "citations"
        ]
