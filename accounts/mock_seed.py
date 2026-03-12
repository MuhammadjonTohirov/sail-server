from __future__ import annotations


MOCK_EMAIL_DOMAIN = "mock.sailuz.test"

_NAME_POOL = [
    ("Azizbek", "Rasulov"),
    ("Dilshod", "Karimov"),
    ("Jasur", "Tursunov"),
    ("Bekzod", "Yuldashev"),
    ("Sherzod", "Nazarov"),
    ("Akmal", "Rakhmonov"),
    ("Oybek", "Saidov"),
    ("Farrux", "Islomov"),
    ("Rustam", "Abduvaliyev"),
    ("Jamshid", "Kadirov"),
    ("Madina", "Usmonova"),
    ("Nilufar", "Kasimova"),
    ("Shahnoza", "Ergasheva"),
    ("Zarina", "Abdullayeva"),
    ("Malika", "Sattorova"),
    ("Gulnoza", "Toshpulatova"),
    ("Feruza", "Muminova"),
    ("Sevara", "Ruzmetova"),
    ("Nargiza", "Yunusova"),
    ("Diyora", "Sobirova"),
]

_ABOUTS = [
    "Quick replies and careful with delivery details.",
    "Usually posts verified items with clear photos.",
    "Open to fair offers and same-day meetings.",
    "Keeps listings updated and responds in the evening.",
    "Mostly sells personal items in good condition.",
]


def build_mock_user_specs(count: int = 20) -> list[dict]:
    specs: list[dict] = []

    for index in range(count):
        first_name, last_name = _NAME_POOL[index % len(_NAME_POOL)]
        sequence = index + 1
        handle = f"{first_name}.{last_name}.{sequence:02d}".lower()
        login = f"{handle}@{MOCK_EMAIL_DOMAIN}"

        specs.append(
            {
                "sequence": sequence,
                "login": login,
                "username": login,
                "email": login,
                "password": f"SailuzDemo{sequence:02d}!",
                "first_name": first_name,
                "last_name": last_name,
                "display_name": f"{first_name} {last_name}",
                "phone_e164": f"+99890{sequence:07d}",
                "avatar_url": f"https://picsum.photos/id/{400 + sequence}/300/300",
                "about": _ABOUTS[index % len(_ABOUTS)],
            }
        )

    return specs
