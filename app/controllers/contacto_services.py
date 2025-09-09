from sqlalchemy.orm import Session
from app.models.contacts import ContactoDriverUS
from datetime import datetime

def save_contacts(db: Session, contacts: list[dict]):
    saved = []
    for c in contacts:
        contact_id = c.get("id")
        name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
        phone = c.get("phone")
        source = c.get("source")
        tags = ",".join(c.get("tags", [])) if isinstance(c.get("tags"), list) else None
        create_date = (
            datetime.fromisoformat(c["dateAdded"].replace("Z", "+00:00"))
            if c.get("dateAdded") else None
        )
        custom_fields = c.get("customFields", [])  # 👈 trae array de GHL

        contacto = db.query(ContactoDriverUS).filter_by(contact_id=contact_id).first()
        if contacto:
            contacto.contact_name = name
            contacto.phone_number = phone
            contacto.source = source
            contacto.tags = tags
            contacto.create_date = create_date
            contacto.asign_to = c.get("ownerId") or None
            contacto.custom_fields = custom_fields   # 👈 se guarda JSON
        else:
            contacto = ContactoDriverUS(
                contact_id=contact_id,
                contact_name=name,
                phone_number=phone,
                source=source,
                tags=tags,
                create_date=create_date,
                asign_to=c.get("ownerId") or None,
                created_at=datetime.utcnow(),
                deleted_at=None,
                call_count=0,
                custom_fields=custom_fields,  # 👈 se guarda JSON
            )
            db.add(contacto)

        saved.append(contacto)

    db.commit()
    return saved