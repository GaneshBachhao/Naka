# backend/scripts/seed_sakri.py
"""Seeds the Sakri region for local development and demos (T10).

Idempotent: if a region with slug "sakri" already exists, this exits
without touching anything, so it's safe to run on every container start.

Locality names below are a REPRESENTATIVE SAMPLE for local development,
not a verified gazetteer of real Sakri taluka villages - Sakri itself and
Pimpalner are real, well-known places in Sakri taluka, Dhule district; the
rest follow plausible Marathi village-naming patterns for the region.
Replace with an authoritative source (Maharashtra LGD codes / census data)
before any production launch.

Business names, owners, and phone numbers are entirely fictional sample
data, not real businesses or people.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import itertools

from naka.catalog.domain.entities import (
    Business,
    Category,
    CategoryTier,
    Locality,
    PublicationState,
    Region,
)
from naka.catalog.domain.value_objects import (
    CategoryNames,
    Coordinates,
    DayHours,
    OpeningHours,
    Weekday,
)
from naka.catalog.infrastructure.repositories import (
    SqlAlchemyBusinessRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyLocalityRepository,
    SqlAlchemyRegionRepository,
)
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId, VerificationId
from naka.shared.domain.phone_number import PhoneNumber
from naka.shared.infrastructure.database import create_engine, create_session_factory
from naka.shared.infrastructure.settings import Settings
from naka.verification.domain.entities import (
    VerificationMethod,
    VerificationRecord,
    VerificationTier,
)
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository

REGION_SLUG = "sakri"

# name_mr, name_en, transliteration, pincode suffix, market_day
_LOCALITIES: list[tuple[str, str, str, str, Weekday | None]] = [
    ("साक्री", "Sakri", "sakri", "304", Weekday.SUNDAY),
    ("पिंपळनेर", "Pimpalner", "pimpalner", "306", Weekday.SUNDAY),
    ("नकाणे", "Nakane", "nakane", "301", None),
    ("रामनगर", "Ramnagar", "ramnagar", "302", Weekday.MONDAY),
    ("कृष्णापूर", "Krushnapur", "krushnapur", "303", None),
    ("गणेशवाडी", "Ganeshwadi", "ganeshwadi", "305", Weekday.TUESDAY),
    ("विठ्ठलनगर", "Vitthalnagar", "vitthalnagar", "307", None),
    ("महादेवखेडे", "Mahadevkhede", "mahadevkhede", "308", Weekday.WEDNESDAY),
    ("सोनवाडी", "Sonwadi", "sonwadi", "309", None),
    ("बोरीपाडा", "Boripada", "boripada", "310", Weekday.THURSDAY),
    ("आंबेगाव", "Ambegaon", "ambegaon", "311", None),
    ("जांभूळखेडे", "Jambhulkhede", "jambhulkhede", "312", Weekday.FRIDAY),
    ("करंजपाडा", "Karanjpada", "karanjpada", "313", None),
    ("वडनगर", "Vadnagar", "vadnagar", "314", Weekday.SATURDAY),
    ("पळसवाडी", "Palaswadi", "palaswadi", "315", None),
    ("भीमानगर", "Bhimanagar", "bhimanagar", "316", Weekday.SUNDAY),
    ("नंदुरखेडे", "Nandurkhede", "nandurkhede", "317", None),
    ("चंद्रपूर", "Chandrapur", "chandrapur", "318", Weekday.MONDAY),
    ("सूर्यवाडी", "Suryawadi", "suryawadi", "319", None),
    ("गिरणगाव", "Girangaon", "girangaon", "320", Weekday.TUESDAY),
    ("धुळेवाडी", "Dhulewadi", "dhulewadi", "321", None),
    ("मोहाडी", "Mohadi", "mohadi", "322", Weekday.WEDNESDAY),
    ("शिरसोळे", "Shirsole", "shirsole", "323", None),
    ("खेडलेझाप", "Khedlejhap", "khedlejhap", "324", Weekday.THURSDAY),
    ("वरखेडी", "Varkhedi", "varkhedi", "325", None),
    ("बाभूळपाडा", "Babhulpada", "babhulpada", "326", Weekday.FRIDAY),
    ("कोळदे", "Kolde", "kolde", "327", None),
    ("मांडळ", "Mandal", "mandal", "328", Weekday.SATURDAY),
    ("उमरखेडे", "Umarkhede", "umarkhede", "329", None),
    ("तळोदे", "Talode", "talode", "330", Weekday.SUNDAY),
    ("नागझरी", "Nagzari", "nagzari", "331", None),
    ("पांझरा", "Panzara", "panzara", "332", Weekday.MONDAY),
    ("हतनूर", "Hatnur", "hatnur", "333", None),
    ("बहिरगाव", "Bahirgaon", "bahirgaon", "334", Weekday.TUESDAY),
    ("रोहिणी", "Rohini", "rohini", "335", None),
    ("शेवाडी", "Shevadi", "shevadi", "336", Weekday.WEDNESDAY),
    ("कवठे", "Kavthe", "kavthe", "337", None),
    ("देवभाने", "Devbhane", "devbhane", "338", Weekday.THURSDAY),
    ("वाघाडी", "Waghadi", "waghadi", "339", None),
    ("लोणखेडे", "Lonkhede", "lonkhede", "340", Weekday.FRIDAY),
]

_CATEGORY_TREE: list[tuple[str, str, CategoryNames, bool]] = [
    ("agriculture", "", CategoryNames(mr="कृषी", hi="कृषि", en="Agriculture"), False),
    (
        "pesticide-dealer",
        "agriculture",
        CategoryNames(
            mr="कृषी सेवा केंद्र",
            hi="कृषि सेवा केंद्र",
            en="Agri-input dealer",
            synonyms_mr=("औषध दुकान", "खत दुकान"),
            transliterations=("krushi seva kendra",),
        ),
        True,
    ),
    ("health", "", CategoryNames(mr="आरोग्य", hi="स्वास्थ्य", en="Health"), False),
    (
        "pharmacy",
        "health",
        CategoryNames(
            mr="औषध दुकान",
            hi="दवा दुकान",
            en="Pharmacy",
            synonyms_mr=("मेडिकल",),
            transliterations=("medical",),
        ),
        True,
    ),
    (
        "clinic",
        "health",
        CategoryNames(mr="दवाखाना", hi="क्लिनिक", en="Clinic", synonyms_mr=("डॉक्टर",)),
        True,
    ),
    ("automotive", "", CategoryNames(mr="वाहन सेवा", hi="वाहन सेवा", en="Automotive"), False),
    (
        "spare-parts-dealer",
        "automotive",
        CategoryNames(
            mr="स्पेअर पार्ट्स दुकान", hi="स्पेयर पार्ट्स दुकान", en="Spare parts dealer"
        ),
        True,
    ),
]

_ROUTABLE_CATEGORY_SLUGS = ["pesticide-dealer", "pharmacy", "clinic", "spare-parts-dealer"]

_BUSINESS_NAME_PAIRS = [
    ("साई कृषी केंद्र", "Sai Krushi Kendra"),
    ("पाटील अ‍ॅग्रो", "Patil Agro"),
    ("जय किसान सेंटर", "Jai Kisan Center"),
    ("गणेश कृषी सेवा", "Ganesh Krushi Seva"),
    ("श्री मेडिकल", "Shree Medical"),
    ("जनता औषधालय", "Janata Aushadhalay"),
    ("संजीवनी फार्मसी", "Sanjeevani Pharmacy"),
    ("आरोग्य मेडिकल", "Arogya Medical"),
    ("डॉ. पवार दवाखाना", "Dr. Pawar Clinic"),
    ("ग्रामीण आरोग्य केंद्र", "Gramin Arogya Kendra"),
    ("शांती क्लिनिक", "Shanti Clinic"),
    ("नवजीवन दवाखाना", "Navjeevan Clinic"),
    ("भारत स्पेअर पार्ट्स", "Bharat Spare Parts"),
    ("ऑटो केअर सेंटर", "Auto Care Center"),
    ("हिंदुस्तान मोटर पार्ट्स", "Hindustan Motor Parts"),
    ("न्यू ऑटो एजन्सी", "New Auto Agency"),
    ("पवार कृषी केंद्र", "Pawar Krushi Kendra"),
    ("महाराष्ट्र मेडिकल स्टोअर्स", "Maharashtra Medical Stores"),
    ("सिद्धिविनायक क्लिनिक", "Siddhivinayak Clinic"),
    ("तुळजाभवानी ऑटो पार्ट्स", "Tuljabhavani Auto Parts"),
]

_OWNER_NAMES = [
    "Ramesh Patil",
    "Suresh More",
    "Anil Deshmukh",
    "Vijay Gaikwad",
    "Sanjay Pawar",
    "Prakash Shinde",
    "Dilip Jadhav",
    "Ravindra Bhosale",
    "Ashok Wagh",
    "Mahesh Sonawane",
    "Rajesh Chavan",
    "Nitin Salunkhe",
    "Bharat Mahajan",
    "Kishor Nikam",
    "Sunil Kale",
    "Vinod Thakur",
    "Sandip Pardeshi",
    "Manoj Kolhe",
    "Yogesh Bhoi",
    "Umesh Gavit",
]


def _daily_hours() -> OpeningHours:
    trading = DayHours(open_time=dt.time(9, 0), close_time=dt.time(21, 0))
    closed = DayHours.closed()
    by_day = {day: trading for day in Weekday}
    by_day[Weekday.SUNDAY] = closed
    return OpeningHours(by_day=by_day)


async def main() -> None:
    engine = create_engine(Settings().database_url)
    session_factory = create_session_factory(engine)
    now = dt.datetime.now(dt.UTC)

    async with session_factory() as session:
        regions = SqlAlchemyRegionRepository(session)
        if await regions.get_by_slug(REGION_SLUG) is not None:
            print(f"Region {REGION_SLUG!r} already seeded - skipping.")
            await engine.dispose()
            return

        region = Region(
            id=RegionId.new(),
            slug=REGION_SLUG,
            name_mr="साक्री",
            name_hi="साक्री",
            name_en="Sakri",
            district="Dhule",
            state="Maharashtra",
            active=True,
        )
        await regions.add(region)

        localities_repo = SqlAlchemyLocalityRepository(session)
        localities: list[Locality] = []
        for name_mr, name_en, translit, pincode_suffix, market_day in _LOCALITIES:
            locality = Locality(
                id=LocalityId.new(),
                region_id=region.id,
                name_mr=name_mr,
                name_en=name_en,
                transliteration_variants=(translit,),
                pincode=f"424{pincode_suffix}",
                centroid=Coordinates(
                    latitude=21.15 + (hash(name_en) % 200 - 100) / 2000,
                    longitude=74.33 + (hash(name_en[::-1]) % 200 - 100) / 2000,
                ),
                market_day=market_day,
            )
            await localities_repo.add(locality)
            localities.append(locality)

        categories_repo = SqlAlchemyCategoryRepository(session)
        category_by_slug: dict[str, Category] = {}
        for slug, parent_slug, names, routable in _CATEGORY_TREE:
            category = Category(
                id=CategoryId.new(),
                slug=slug,
                parent_id=category_by_slug[parent_slug].id if parent_slug else None,
                names=names,
                tier=CategoryTier.TIER_1,
                routable=routable,
            )
            await categories_repo.add(category)
            category_by_slug[slug] = category

        routable_categories = [category_by_slug[slug] for slug in _ROUTABLE_CATEGORY_SLUGS]

        businesses_repo = SqlAlchemyBusinessRepository(session)
        verification_repo = SqlAlchemyVerificationRecordRepository(session)
        locality_cycle = itertools.cycle(localities)
        pairs = zip(_BUSINESS_NAME_PAIRS, _OWNER_NAMES, strict=True)
        for i, ((name_mr, name_en), owner) in enumerate(pairs):
            category = routable_categories[i % len(routable_categories)]
            locality = next(locality_cycle)
            phone = PhoneNumber(f"98765{40001 + i}")
            business = Business(
                id=BusinessId.new(),
                region_id=region.id,
                locality_id=locality.id,
                name_mr=name_mr,
                name_en=name_en,
                owner_name=owner,
                category_ids=(category.id,),
                contact_numbers=(phone,),
                whatsapp_number=phone,
                landmark=f"{locality.name_mr} बस स्टँड जवळ",
                coordinates=locality.centroid,
                opening_hours=_daily_hours(),
                attributes=frozenset(),
                publication_state=PublicationState.PUBLISHED_VERIFIED,
            )
            await businesses_repo.add(business)

            verification = VerificationRecord(
                id=VerificationId.new(),
                business_id=business.id,
                tier=VerificationTier.OWNER_CONFIRMED,
                method=VerificationMethod.PHONE_CALL,
                verified_at=now - dt.timedelta(days=i),
                verified_by="Seed script",
                notes="Seed data for local development",
            )
            await verification_repo.add(verification)

        await session.commit()

    print(
        f"Seeded region={REGION_SLUG!r}, {len(_LOCALITIES)} localities, "
        f"{len(category_by_slug)} categories, {len(_BUSINESS_NAME_PAIRS)} businesses."
    )
    await engine.dispose()


asyncio.run(main())
