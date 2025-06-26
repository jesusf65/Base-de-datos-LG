from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from app.core.database import Base

class BaseModel(Base):  
    __abstract__ = True 

    @hybrid_property
    def is_deleted(self):
        return self.deleted_at is not None  

    @is_deleted.expression
    def is_deleted(cls):
        return cls.deleted_at.isnot(None)   
        
    def soft_delete(self):
        self.deleted_at = func.now()
        
        
        #Esto posibilita hacer soft delete