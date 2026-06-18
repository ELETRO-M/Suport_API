import os
import sys
import re
from urllib.parse import urlparse
from decouple import config

import cloudinary
import cloudinary.uploader
import cloudinary.utils

cloudinary.config(
    cloud_name=config("CLOUDINARY_CLOUD_NAME"),
    api_key=config("CLOUDINARY_API_KEY"),
    api_secret=config("CLOUDINARY_API_SECRET"),
    secure=True,
)


def extrair_public_id(url: str) -> str:
    path = urlparse(url).path
    path = re.sub(r"^/.+?/upload/", "", path)
    path = re.sub(r"^v\d+/", "", path)
    return path.rsplit(".", 1)[0]


def obter_url_visualizacao(public_id: str, page: int = 1, out_format: str = "jpg") -> str:
    """Gera URL com marca de água CONFIDENCIAL renderizando a página do PDF como imagem."""
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type="image",
        transformation=[
            {
                "overlay": {
                    "font_family": "Arial",
                    "font_size": 60,
                    "text": "CONFIDENCIAL",
                },
                "gravity": "center",
                "opacity": 30,
                "color": "red",
            },
            {"flags": "layer_apply"},
            {"page": page},
            {"fetch_format": out_format},
        ],
    )
    return url


def teste_upload(caminho_arquivo: str):
    print(f"-> Fazendo upload de: {caminho_arquivo}")
    result = cloudinary.uploader.upload(
        caminho_arquivo,
        resource_type="image",   # IMPORTANTE: image, não raw, para permitir transformação
        folder="testes/anexos",
        overwrite=True,
    )
    print("Upload OK")
    print("public_id:", result["public_id"])
    print("secure_url (original):", result["secure_url"])
    return result


def teste_extracao(url: str):
    public_id = extrair_public_id(url)
    print("public_id extraído:", public_id)
    return public_id


def teste_watermark(public_id: str):
    url = obter_url_visualizacao(public_id)
    print("URL com marca de água:", url)
    return url
x=extrair_public_id("https://res.cloudinary.com/ds8gskjme/raw/upload/v1/media/intervencoes/anexos/documento_teste_sli48x.pdf")
teste_watermark(x)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_cloudinary_manual.py caminho/para/arquivo.pdf")
        sys.exit(1)

    caminho = sys.argv[1]

    # 1. Upload
    result = teste_upload(caminho)

    # 2. Extração do public_id a partir da URL retornada (simula o fluxo real)
    public_id = teste_extracao(result["secure_url"])

    # 3. Geração da URL com marca de água
    url_marcada = teste_watermark(public_id)

    print("\nAbra essa URL no navegador para verificar visualmente:")
    print(url_marcada)