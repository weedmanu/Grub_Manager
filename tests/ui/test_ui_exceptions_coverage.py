
import pytest
from ui.ui_exceptions import UiError, UiValidationError, UiWidgetError, UiStateError

def test_ui_exceptions():
    with pytest.raises(UiError):
        raise UiError("Error")
    
    with pytest.raises(UiValidationError):
        raise UiValidationError("Validation Error")
        
    with pytest.raises(UiWidgetError):
        raise UiWidgetError("Widget Error")
        
    with pytest.raises(UiStateError):
        raise UiStateError("State Error")
