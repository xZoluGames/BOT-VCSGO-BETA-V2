"""
Sistema de Excepciones Personalizado - BOT-VCSGO-BETA-V2

Define excepciones específicas para diferentes tipos de errores en el bot.
Mejora el debugging y permite manejo específico de errores.
"""

from typing import Optional, Dict, Any
import traceback
from datetime import datetime


class BotException(Exception):
    """
    Excepción base para todas las excepciones del bot
    
    Attributes:
        message: Mensaje de error
        details: Detalles adicionales del error
        timestamp: Momento en que ocurrió el error
        error_code: Código único del error para tracking
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None):
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.error_code = error_code or self.__class__.__name__
        self.traceback = traceback.format_exc()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para logging/serialización"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'exception_type': self.__class__.__name__,
            'traceback': self.traceback
        }


# Excepciones de Configuración
class ConfigurationError(BotException):
    """Error en la configuración del sistema"""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Clave API requerida no encontrada"""
    
    def __init__(self, platform: str, env_var: Optional[str] = None):
        details = {
            'platform': platform,
            'env_var': env_var or f"{platform.upper()}_API_KEY"
        }
        message = f"API key missing for platform '{platform}'"
        if env_var:
            message += f". Please set environment variable '{env_var}'"
        
        super().__init__(message, details, error_code="MISSING_API_KEY")


class InvalidConfigurationError(ConfigurationError):
    """Configuración inválida detectada"""
    
    def __init__(self, config_name: str, reason: str):
        details = {
            'config_name': config_name,
            'reason': reason
        }
        message = f"Invalid configuration '{config_name}': {reason}"
        super().__init__(message, details, error_code="INVALID_CONFIG")


# Excepciones de Scraping
class ScrapingError(BotException):
    """Error base para operaciones de scraping"""
    pass


class APIError(ScrapingError):
    """Error al interactuar con una API externa"""
    
    def __init__(self, platform: str, status_code: Optional[int] = None, 
                 response_text: Optional[str] = None, url: Optional[str] = None):
        details = {
            'platform': platform,
            'status_code': status_code,
            'response_text': response_text[:500] if response_text else None,  # Limitar tamaño
            'url': url
        }
        
        message = f"API error for platform '{platform}'"
        if status_code:
            message += f" (HTTP {status_code})"
        
        super().__init__(message, details, error_code=f"API_ERROR_{platform.upper()}")


class RateLimitError(APIError):
    """Error por exceder límite de rate de API"""
    
    def __init__(self, platform: str, retry_after: Optional[int] = None):
        details = {
            'platform': platform,
            'retry_after': retry_after
        }
        
        message = f"Rate limit exceeded for platform '{platform}'"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        super().__init__(platform, status_code=429)
        self.details.update(details)
        self.error_code = f"RATE_LIMIT_{platform.upper()}"


class ParseError(ScrapingError):
    """Error al parsear datos de respuesta"""
    
    def __init__(self, platform: str, data_type: str, reason: str):
        details = {
            'platform': platform,
            'data_type': data_type,
            'reason': reason
        }
        
        message = f"Failed to parse {data_type} from '{platform}': {reason}"
        super().__init__(message, details, error_code=f"PARSE_ERROR_{platform.upper()}")


class ValidationError(ScrapingError):
    """Error en validación de datos"""
    
    def __init__(self, field: str, value: Any, reason: str):
        details = {
            'field': field,
            'value': str(value)[:100],  # Limitar tamaño
            'reason': reason
        }
        
        message = f"Validation failed for field '{field}': {reason}"
        super().__init__(message, details, error_code="VALIDATION_ERROR")


# Excepciones de Proxy
class ProxyError(BotException):
    """Error base para operaciones de proxy"""
    pass


class ProxyAuthenticationError(ProxyError):
    """Error de autenticación con servicio de proxy"""
    
    def __init__(self, service: str = "Oculus"):
        details = {
            'service': service,
            'hint': "Check OCULUS_AUTH_TOKEN and OCULUS_ORDER_TOKEN environment variables"
        }
        
        message = f"Failed to authenticate with {service} proxy service"
        super().__init__(message, details, error_code="PROXY_AUTH_ERROR")


class ProxyConnectionError(ProxyError):
    """Error de conexión a través de proxy"""
    
    def __init__(self, proxy_url: str, reason: str):
        # Ocultar credenciales del proxy en el mensaje
        safe_url = proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url
        
        details = {
            'proxy': safe_url,
            'reason': reason
        }
        
        message = f"Proxy connection failed: {reason}"
        super().__init__(message, details, error_code="PROXY_CONNECTION_ERROR")


class NoProxiesAvailableError(ProxyError):
    """No hay proxies disponibles"""
    
    def __init__(self, region: Optional[str] = None):
        details = {
            'region': region
        }
        
        message = "No proxies available"
        if region:
            message += f" for region '{region}'"
        
        super().__init__(message, details, error_code="NO_PROXIES_AVAILABLE")


# Excepciones de Cache
class CacheError(BotException):
    """Error base para operaciones de cache"""
    pass


class CacheWriteError(CacheError):
    """Error al escribir en cache"""
    
    def __init__(self, key: str, reason: str):
        details = {
            'key': key,
            'reason': reason
        }
        
        message = f"Failed to write to cache for key '{key}': {reason}"
        super().__init__(message, details, error_code="CACHE_WRITE_ERROR")


class CacheReadError(CacheError):
    """Error al leer del cache"""
    
    def __init__(self, key: str, reason: str):
        details = {
            'key': key,
            'reason': reason
        }
        
        message = f"Failed to read from cache for key '{key}': {reason}"
        super().__init__(message, details, error_code="CACHE_READ_ERROR")


# Excepciones de Análisis
class AnalysisError(BotException):
    """Error base para análisis de rentabilidad"""
    pass


class InsufficientDataError(AnalysisError):
    """Datos insuficientes para análisis"""
    
    def __init__(self, required_platforms: int, found_platforms: int):
        details = {
            'required_platforms': required_platforms,
            'found_platforms': found_platforms
        }
        
        message = f"Insufficient data for analysis. Required: {required_platforms} platforms, Found: {found_platforms}"
        super().__init__(message, details, error_code="INSUFFICIENT_DATA")


class CalculationError(AnalysisError):
    """Error en cálculos de rentabilidad"""
    
    def __init__(self, calculation_type: str, reason: str):
        details = {
            'calculation_type': calculation_type,
            'reason': reason
        }
        
        message = f"Calculation error in '{calculation_type}': {reason}"
        super().__init__(message, details, error_code="CALCULATION_ERROR")


# Excepciones de Sistema
class SystemError(BotException):
    """Error base para problemas del sistema"""
    pass


class ResourceError(SystemError):
    """Error de recursos del sistema"""
    
    def __init__(self, resource_type: str, reason: str):
        details = {
            'resource_type': resource_type,
            'reason': reason
        }
        
        message = f"Resource error ({resource_type}): {reason}"
        super().__init__(message, details, error_code="RESOURCE_ERROR")


class FileSystemError(SystemError):
    """Error del sistema de archivos"""
    
    def __init__(self, operation: str, path: str, reason: str):
        details = {
            'operation': operation,
            'path': path,
            'reason': reason
        }
        
        message = f"File system error during '{operation}' on '{path}': {reason}"
        super().__init__(message, details, error_code="FILESYSTEM_ERROR")


# Utilidades para manejo de errores
class ErrorHandler:
    """
    Manejador centralizado de errores
    
    Proporciona métodos para manejar y registrar errores de manera consistente.
    """
    
    @staticmethod
    def handle_api_error(platform: str, error: Exception, logger=None) -> Optional[APIError]:
        """
        Maneja errores de API y los convierte a excepciones específicas
        
        Args:
            platform: Plataforma donde ocurrió el error
            error: Excepción original
            logger: Logger opcional para registrar el error
            
        Returns:
            APIError específico o None si no se puede manejar
        """
        import requests
        
        if isinstance(error, requests.exceptions.RequestException):
            response = getattr(error, 'response', None)
            
            if response is not None:
                status_code = response.status_code
                
                # Rate limit
                if status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    api_error = RateLimitError(
                        platform,
                        retry_after=int(retry_after) if retry_after else None
                    )
                else:
                    api_error = APIError(
                        platform,
                        status_code=status_code,
                        response_text=response.text,
                        url=str(response.url)
                    )
            else:
                # Error de conexión
                api_error = APIError(
                    platform,
                    response_text=str(error)
                )
            
            if logger:
                logger.error(f"API Error: {api_error.to_dict()}")
            
            return api_error
        
        return None
    
    @staticmethod
    def log_exception(exception: BotException, logger) -> None:
        """
        Registra una excepción del bot de manera estructurada
        
        Args:
            exception: Excepción a registrar
            logger: Logger a usar
        """
        error_dict = exception.to_dict()
        
        # Log con diferentes niveles según el tipo
        if isinstance(exception, (RateLimitError, ValidationError)):
            logger.warning(f"[{exception.error_code}] {exception.message}", extra=error_dict)
        elif isinstance(exception, (ConfigurationError, SystemError)):
            logger.error(f"[{exception.error_code}] {exception.message}", extra=error_dict)
        else:
            logger.error(f"[{exception.error_code}] {exception.message}", extra=error_dict)
    
    @staticmethod
    def create_error_report(exceptions: list[BotException]) -> Dict[str, Any]:
        """
        Crea un reporte de errores para análisis
        
        Args:
            exceptions: Lista de excepciones a reportar
            
        Returns:
            Diccionario con estadísticas de errores
        """
        report = {
            'total_errors': len(exceptions),
            'errors_by_type': {},
            'errors_by_platform': {},
            'errors_by_code': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for exc in exceptions:
            # Por tipo
            exc_type = type(exc).__name__
            report['errors_by_type'][exc_type] = report['errors_by_type'].get(exc_type, 0) + 1
            
            # Por plataforma (si aplica)
            if 'platform' in exc.details:
                platform = exc.details['platform']
                report['errors_by_platform'][platform] = report['errors_by_platform'].get(platform, 0) + 1
            
            # Por código
            report['errors_by_code'][exc.error_code] = report['errors_by_code'].get(exc.error_code, 0) + 1
        
        return report