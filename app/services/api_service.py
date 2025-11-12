"""
Servicio de APIs Externas (POO)
Sistema extensible para obtener tasas de cambio de múltiples fuentes
"""
import requests
from datetime import datetime
from abc import ABC, abstractmethod

class ExchangeRateAPI(ABC):
    """Clase base abstracta para proveedores de APIs"""
    
    @abstractmethod
    def get_rate(self, from_currency, to_currency):
        """
        Obtener tasa de cambio
        Retorna: (rate, error)
        """
        pass
    
    @abstractmethod
    def get_name(self):
        """Nombre del proveedor"""
        pass


class ExchangeRateAPIProvider(ExchangeRateAPI):
    """
    Proveedor: exchangerate-api.com
    Gratis: 1,500 requests/mes
    URL: https://www.exchangerate-api.com/
    """
    
    def __init__(self, api_key=None):
        self.base_url = "https://api.exchangerate-api.com/v4/latest"
        self.api_key = api_key
    
    def get_rate(self, from_currency='USD', to_currency='EUR'):
        """Obtener tasa de cambio USD → EUR"""
        try:
            url = f"{self.base_url}/{from_currency}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = data['rates'].get(to_currency)
            
            if rate:
                return float(rate), None
            else:
                return None, f"Moneda {to_currency} no encontrada"
                
        except requests.exceptions.RequestException as e:
            return None, f"Error de conexión: {str(e)}"
        except (KeyError, ValueError) as e:
            return None, f"Error procesando respuesta: {str(e)}"
    
    def get_name(self):
        return "ExchangeRate-API"


class CurrencyAPIProvider(ExchangeRateAPI):
    """
    Proveedor: currencyapi.com
    Gratis: 300 requests/mes
    URL: https://currencyapi.com/
    """
    
    def __init__(self, api_key):
        self.base_url = "https://api.currencyapi.com/v3/latest"
        self.api_key = api_key
    
    def get_rate(self, from_currency='USD', to_currency='EUR'):
        """Obtener tasa de cambio"""
        if not self.api_key:
            return None, "API key no configurada"
        
        try:
            params = {
                'apikey': self.api_key,
                'base_currency': from_currency,
                'currencies': to_currency
            }
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = data['data'][to_currency]['value']
            
            return float(rate), None
                
        except requests.exceptions.RequestException as e:
            return None, f"Error de conexión: {str(e)}"
        except (KeyError, ValueError) as e:
            return None, f"Error procesando respuesta: {str(e)}"
    
    def get_name(self):
        return "CurrencyAPI"


class FreeCurrencyAPIProvider(ExchangeRateAPI):
    """
    Proveedor: freecurrencyapi.com
    Gratis: 5,000 requests/mes
    URL: https://freecurrencyapi.com/
    """
    
    def __init__(self, api_key=None):
        self.base_url = "https://api.freecurrencyapi.com/v1/latest"
        self.api_key = api_key
    
    def get_rate(self, from_currency='USD', to_currency='EUR'):
        """Obtener tasa de cambio"""
        try:
            params = {
                'base_currency': from_currency,
                'currencies': to_currency
            }
            if self.api_key:
                params['apikey'] = self.api_key
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = data['data'][to_currency]
            
            return float(rate), None
                
        except requests.exceptions.RequestException as e:
            return None, f"Error de conexión: {str(e)}"
        except (KeyError, ValueError) as e:
            return None, f"Error procesando respuesta: {str(e)}"
    
    def get_name(self):
        return "FreeCurrencyAPI"


class ExchangeRateHostProvider(ExchangeRateAPI):
    """
    Proveedor: exchangerate.host
    Gratis: ilimitado (sin API key)
    URL: https://exchangerate.host/
    """
    
    def __init__(self):
        self.base_url = "https://api.exchangerate.host/latest"
    
    def get_rate(self, from_currency='USD', to_currency='EUR'):
        """Obtener tasa de cambio"""
        try:
            params = {
                'base': from_currency,
                'symbols': to_currency
            }
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                rate = data['rates'].get(to_currency)
                return float(rate), None
            else:
                return None, "API retornó error"
                
        except requests.exceptions.RequestException as e:
            return None, f"Error de conexión: {str(e)}"
        except (KeyError, ValueError) as e:
            return None, f"Error procesando respuesta: {str(e)}"
    
    def get_name(self):
        return "ExchangeRate.host"


class APIService:
    """Servicio principal para gestionar múltiples proveedores de APIs"""
    
    # Proveedores disponibles
    PROVIDERS = {
        'exchangerate-api': ExchangeRateAPIProvider,
        'exchangerate-host': ExchangeRateHostProvider,
        'currency-api': CurrencyAPIProvider,
        'freecurrency-api': FreeCurrencyAPIProvider,
    }
    
    @staticmethod
    def get_provider(provider_name, api_key=None):
        """Obtener instancia de un proveedor"""
        provider_class = APIService.PROVIDERS.get(provider_name)
        
        if not provider_class:
            return None
        
        # Proveedores que necesitan API key
        if provider_class in [CurrencyAPIProvider, FreeCurrencyAPIProvider]:
            return provider_class(api_key)
        else:
            return provider_class()
    
    @staticmethod
    def fetch_rate(from_currency='USD', to_currency='EUR', provider_name='exchangerate-host', api_key=None):
        """
        Obtener tasa de cambio usando un proveedor específico
        Retorna: (rate, provider_name, error)
        """
        provider = APIService.get_provider(provider_name, api_key)
        
        if not provider:
            return None, None, f"Proveedor '{provider_name}' no encontrado"
        
        rate, error = provider.get_rate(from_currency, to_currency)
        
        if error:
            return None, provider.get_name(), error
        
        return rate, provider.get_name(), None
    
    @staticmethod
    def fetch_rate_with_fallback(from_currency='USD', to_currency='EUR'):
        """
        Intentar obtener tasa usando múltiples proveedores (fallback)
        Retorna: (rate, provider_used, error)
        """
        # Orden de prioridad (los gratuitos sin API key primero)
        priority_order = [
            'exchangerate-host',
            'exchangerate-api',
            'freecurrency-api',
        ]
        
        errors = []
        
        for provider_name in priority_order:
            rate, provider_used, error = APIService.fetch_rate(
                from_currency, to_currency, provider_name
            )
            
            if rate:
                return rate, provider_used, None
            else:
                errors.append(f"{provider_name}: {error}")
        
        # Si todos fallaron
        return None, None, " | ".join(errors)
    
    @staticmethod
    def get_available_providers():
        """Listar proveedores disponibles"""
        return list(APIService.PROVIDERS.keys())
