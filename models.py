from datetime import datetime
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy

# Create db instance
db = SQLAlchemy()


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), default='ARS')  # USD or ARS
    year = db.Column(db.Integer)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    kilometers = db.Column(db.Integer)
    fuel_type = db.Column(db.String(50))
    transmission = db.Column(db.String(50))
    color = db.Column(db.String(50))
    images = db.Column(db.Text)  # JSON string of image URLs
    main_image_index = db.Column(
        db.Integer, default=0)  # Index of the main image to display
    whatsapp_number = db.Column(db.String(20),
                                nullable=True)  # WhatsApp number
    call_number = db.Column(db.String(20), nullable=True)  # Call number
    contact_type = db.Column(
        db.String(20), default="whatsapp")  # 'whatsapp' or 'call' (deprecated)
    phone_number = db.Column(
        db.String(20), nullable=True)  # For call-only contact (deprecated)
    is_active = db.Column(db.Boolean, default=True)
    is_plus = db.Column(
        db.Boolean,
        default=True)  # True for Plus (complete), False for Free (basic)
    premium_duration_months = db.Column(
        db.Integer, default=1)  # Duration of premium visibility in months
    premium_expires_at = db.Column(
        db.DateTime, nullable=True)  # When premium visibility expires
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    location = db.Column(db.String(50), nullable=True)  # Tunuyán, Tupungato, San Carlos
    tire_condition = db.Column(db.String(50), nullable=True)  # Estado de Cubiertas
    client_request_id = db.Column(
        db.Integer, db.ForeignKey('client_request.id'), nullable=True
    )  # Link to original request if created from client request

    # Relationships
    clicks = db.relationship('Click',
                             backref='vehicle',
                             lazy=True,
                             cascade='all, delete-orphan')

    def get_images_list(self):
        if self.images:
            import json
            try:
                images = json.loads(self.images)
                # Convert relative paths to full URLs for Flask
                processed_images = []
                for img in images:
                    if img.startswith('uploads/'):
                        from flask import url_for
                        processed_images.append(url_for('static',
                                                        filename=img))
                    else:
                        processed_images.append(img)
                return processed_images
            except:
                return []
        return []

    def get_main_image(self):
        images = self.get_images_list()
        if images:
            # Use the main_image_index to get the selected main image
            main_index = self.main_image_index if self.main_image_index < len(
                images) else 0
            main_image = images[main_index]

            # If it's a local file path, add static/ prefix for Flask url_for
            if main_image.startswith('uploads/'):
                from flask import url_for
                return url_for('static', filename=main_image)
            return main_image
        
        # Return placeholder for both free and plus plans without images
        from flask import url_for
        return url_for('static', filename='placeholder-car.png')

    def format_price(self):
        """Formatea el precio con símbolo de moneda"""
        currency_symbol = "$" if self.currency == "ARS" else "USD $"
        return f"{currency_symbol}{self.price:,}".replace(",", ".")

    def format_price_with_currency(self):
        """Formatea el precio con símbolo de moneda y etiqueta de moneda"""
        if self.currency == "ARS":
            return f"${self.price:,} ARS".replace(",", ".")
        else:
            return f"${self.price:,} USD".replace(",", ".")

    def format_price_only(self):
        """Formatea solo el precio sin símbolo de moneda"""
        return f"{self.price:,}".replace(",", ".")

    def get_currency_class(self):
        """Retorna la clase CSS para el color de la moneda"""
        return "price-ars" if self.currency == "ARS" else "price-usd"

    def get_currency_badge_class(self):
        """Retorna la clase CSS para el badge de la moneda"""
        return "price-badge-ars" if self.currency == "ARS" else "price-badge-usd"

    def get_whatsapp_contact_message(self):
        return f"Hola! Me interesa el vehículo: {self.title} - Precio: {self.format_price()} {self.currency}. Link: {self.get_full_url()}"

    def get_whatsapp_offer_message(self, offer_amount):
        return f"Hola! Quiero hacer una oferta por: {self.title} - Precio de venta: {self.format_price()} {self.currency} - Mi oferta: ${offer_amount:,} {self.currency}. Link: {self.get_full_url()}".replace(
            ",", ".")

    def get_contact_number(self):
        """Retorna el número de contacto según el tipo (método legacy)"""
        if self.contact_type == 'call' and self.phone_number:
            return self.phone_number
        return self.whatsapp_number

    def get_contact_type_display(self):
        """Retorna el tipo de contacto para mostrar (método legacy)"""
        return "WhatsApp" if self.contact_type == "whatsapp" else "Llamada"

    def get_whatsapp_number(self):
        """Retorna el número de WhatsApp si está disponible"""
        return self.whatsapp_number if self.whatsapp_number else None

    def get_call_number(self):
        """Retorna el número de llamada si está disponible"""
        return self.call_number if self.call_number else None

    def has_whatsapp(self):
        """Verifica si tiene número de WhatsApp"""
        return bool(self.whatsapp_number)

    def has_call(self):
        """Verifica si tiene número de llamada"""
        return bool(self.call_number)

    def get_contact_buttons(self):
        """Retorna información de los botones de contacto disponibles"""
        buttons = []
        if self.has_whatsapp():
            buttons.append({
                'type': 'whatsapp',
                'number': self.whatsapp_number,
                'text': 'Contacto WhatsApp',
                'icon': 'fab fa-whatsapp',
                'class': 'btn-success'
            })
        if self.has_call():
            buttons.append({
                'type': 'call',
                'number': self.call_number,
                'text': 'Llamar Ahora',
                'icon': 'fas fa-phone',
                'class': 'btn-primary'
            })
        return buttons

    def is_premium_active(self):
        """Verifica si el vehículo tiene visibilidad premium activa"""
        if not self.is_plus:
            return False
        if not self.premium_expires_at:
            return True
        return self.premium_expires_at > datetime.utcnow()

    def get_full_url(self):
        from flask import url_for, request
        return request.host_url.rstrip('/') + url_for('vehicle_detail',
                                                      id=self.id)

    def get_location(self):
        """Get vehicle location, either direct or from client request"""
        if self.location:
            return self.location
        elif self.client_request_id:
            client_request = ClientRequest.query.get(self.client_request_id)
            if client_request and client_request.location:
                return client_request.location
        return "Valle de Uco"  # Default location
    
    def get_tire_condition_display(self):
        """Get tire condition display text"""
        tire_conditions = {
            'excelente': 'Excelente',
            'muy_bueno': 'Muy Bueno',
            'bueno': 'Bueno',
            'regular': 'Regular',
            'malo': 'Malo'
        }
        return tire_conditions.get(self.tire_condition, 'No especificado')
    
    def get_tire_condition_class(self):
        """Get CSS class for tire condition"""
        tire_classes = {
            'excelente': 'text-success',
            'muy_bueno': 'text-info',
            'bueno': 'text-primary',
            'regular': 'text-warning',
            'malo': 'text-danger'
        }
        return tire_classes.get(self.tire_condition, 'text-muted')


class Click(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer,
                           db.ForeignKey('vehicle.id'),
                           nullable=False)
    click_type = db.Column(db.String(20),
                           nullable=False)  # 'whatsapp' or 'offer'
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class VehicleView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer,
                           db.ForeignKey('vehicle.id'),
                           nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle = db.relationship('Vehicle', backref='views')


class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Personal information
    full_name = db.Column(db.String(200), nullable=False)
    dni = db.Column(db.String(20), nullable=False)
    whatsapp_number = db.Column(db.String(20),
                                nullable=True)  # WhatsApp number
    call_number = db.Column(db.String(20), nullable=True)  # Call number
    phone_number = db.Column(db.String(20),
                             nullable=True)  # Legacy field for compatibility
    location = db.Column(db.String(50),
                         nullable=False)  # Tunuyán, Tupungato, San Carlos
    address = db.Column(db.String(500), nullable=True)  # Optional address

    # Vehicle information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False)  # USD or ARS
    year = db.Column(db.Integer)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    kilometers = db.Column(db.Integer)
    fuel_type = db.Column(db.String(50))
    transmission = db.Column(db.String(50))
    color = db.Column(db.String(50))
    images = db.Column(db.Text)  # JSON string of image URLs
    main_image_index = db.Column(db.Integer,
                                 default=0)  # Index of the main image
    publication_type = db.Column(db.String(10),
                                 default='plus')  # 'free' or 'plus'

    # Request status
    status = db.Column(db.String(20),
                       default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)  # Notes from admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by_admin_id = db.Column(db.Integer,
                                      db.ForeignKey('admin.id'),
                                      nullable=True)

    # Relationships
    processed_by_admin = db.relationship('Admin', backref='processed_requests')
    created_vehicle = db.relationship('Vehicle',
                                      backref='original_request',
                                      uselist=False)

    def get_images_list(self):
        if self.images:
            import json
            try:
                images = json.loads(self.images)
                # Convert relative paths to full URLs for Flask
                processed_images = []
                for img in images:
                    if img.startswith('uploads/'):
                        from flask import url_for
                        processed_images.append(url_for('static',
                                                        filename=img))
                    else:
                        processed_images.append(img)
                return processed_images
            except:
                return []
        return []

    def get_main_image(self):
        images = self.get_images_list()
        if images:
            return images[0]
        return "/static/placeholder-car.png"

    def format_price(self):
        """Formatea el precio con símbolo de moneda"""
        currency_symbol = "$" if self.currency == "ARS" else "USD $"
        return f"{currency_symbol}{self.price:,}".replace(",", ".")

    def format_price_with_currency(self):
        """Formatea el precio con símbolo de moneda y etiqueta de moneda"""
        if self.currency == "ARS":
            return f"${self.price:,} ARS".replace(",", ".")
        else:
            return f"${self.price:,} USD".replace(",", ".")

    def format_price_only(self):
        """Formatea solo el precio sin símbolo de moneda"""
        return f"{self.price:,}".replace(",", ".")

    def get_currency_class(self):
        """Retorna la clase CSS para el color de la moneda"""
        return "price-ars" if self.currency == "ARS" else "price-usd"

    def get_currency_badge_class(self):
        """Retorna la clase CSS para el badge de la moneda"""
        return "price-badge-ars" if self.currency == "ARS" else "price-badge-usd"

    def get_whatsapp_contact_url(self):
        """Generate WhatsApp contact URL for admin to contact client"""
        message = f"Hola {self.full_name}! Te contacto sobre tu solicitud de publicación del vehículo: {self.title}. ¿Podemos hablar sobre algunos detalles?"
        import urllib.parse
        # Use WhatsApp number first, then call number, then legacy phone number
        contact_number = self.whatsapp_number or self.call_number or self.phone_number
        if contact_number:
            return f"https://wa.me/{contact_number.replace('+', '')}?text={urllib.parse.quote(message)}"
        return None


class PageVisit(db.Model):
    """Model to track page visits"""
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(100),
                     nullable=False)  # 'index', 'vehicle_detail', etc.
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.Text, nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PageVisit {self.page} - {self.created_at}>'


class Gestor(db.Model):
    """Model for automotive managers/brokers"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    business_name = db.Column(
        db.String(150))  # Nombre de la empresa/concesionario
    phone_number = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    location = db.Column(db.String(100))  # Ciudad/zona
    specializations = db.Column(
        db.Text)  # Especialidades (marcas que maneja, etc.)
    years_experience = db.Column(db.Integer)
    description = db.Column(db.Text)
    image_filename = db.Column(db.String(255))  # Nombre del archivo de imagen del gestor
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)  # Gestores destacados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def get_image_url(self):
        """Get image URL for gestor"""
        if self.image_filename:
            from flask import url_for
            return url_for('static', filename=f'uploads/gestores/{self.image_filename}')
        return url_for('static', filename='placeholder-person.png')

    def get_whatsapp_contact_url(self):
        """Generate WhatsApp contact URL"""
        if self.whatsapp_number:
            message = f"Hola {self.name}! Te contacto desde MarketplaceVUco para consultar sobre servicios de gestión automotor."
            import urllib.parse
            return f"https://wa.me/{self.whatsapp_number.replace('+', '')}?text={urllib.parse.quote(message)}"
        return None

    def get_phone_contact_url(self):
        """Generate phone call URL"""
        if self.phone_number:
            return f"tel:{self.phone_number}"
        return None

    def format_experience(self):
        """Format years of experience"""
        if self.years_experience:
            return f"{self.years_experience} año{'s' if self.years_experience != 1 else ''} de experiencia"
        return "Experiencia no especificada"

    def __repr__(self):
        return f'<Gestor {self.name} - {self.location}>'
