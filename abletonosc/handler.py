from ableton.v2.control_surface.component import Component
from typing import Optional, Tuple, Any
import logging
from .osc_server import OSCServer

class AbletonOSCHandler(Component):
    def __init__(self, manager):
        super().__init__()

        self.logger = logging.getLogger("abletonosc")
        self.manager = manager
        self.osc_server: OSCServer = self.manager.osc_server
        self.listener_functions = {}
        self.class_identifier = None
        self.init_api()

    def init_api(self):
        pass

    def clear_api(self):
        """Clear all listeners when shutting down."""
        # Remove all listeners safely
        for listener_key in list(self.listener_functions.keys()):
            try:
                # Extract the property and params from the key
                if isinstance(listener_key, tuple) and len(listener_key) >= 2:
                    prop = listener_key[0]
                    params = listener_key[1] if len(listener_key) > 1 else ()
                    
                    # Determine track type and index from the key
                    if prop.startswith("return_"):
                        # Return track listener
                        actual_prop = prop[7:]  # Remove "return_" prefix
                        if params:
                            track_index = params[0]
                            if track_index < len(self.song.return_tracks):
                                track = self.song.return_tracks[track_index]
                                self._safe_remove_listener(track, actual_prop, listener_key)
                    else:
                        # Regular track listener
                        if params:
                            track_index = params[0]
                            if track_index < len(self.song.tracks):
                                track = self.song.tracks[track_index]
                                self._safe_remove_listener(track, prop, listener_key)
            except Exception as e:
                self.logger.warning(f"Error removing listener {listener_key}: {e}")
        
        self.listener_functions.clear()

    def _safe_remove_listener(self, target, prop, listener_key):
        """Safely remove a listener, handling both regular and mixer properties."""
        try:
            listener_function = self.listener_functions.get(listener_key)
            if not listener_function:
                return
                
            # Check if it's a mixer property
            if hasattr(target, 'mixer_device') and hasattr(target.mixer_device, prop):
                parameter_object = getattr(target.mixer_device, prop)
                if hasattr(parameter_object, 'remove_value_listener'):
                    parameter_object.remove_value_listener(listener_function)
            else:
                # Regular property
                remove_listener_function_name = f"remove_{prop}_listener"
                if hasattr(target, remove_listener_function_name):
                    remove_listener_function = getattr(target, remove_listener_function_name)
                    remove_listener_function(listener_function)
                    
            del self.listener_functions[listener_key]
        except Exception as e:
            self.logger.debug(f"Could not remove listener for {prop}: {e}")

    #--------------------------------------------------------------------------------
    # Generic callbacks
    #--------------------------------------------------------------------------------
    def _call_method(self, target, method, params: Optional[Tuple] = ()):
        self.logger.info("Calling method for %s: %s (params %s)" % (self.class_identifier, method, str(params)))
        getattr(target, method)(*params)

    def _set_property(self, target, prop, params: Tuple) -> None:
        self.logger.info("Setting property for %s: %s (new value %s)" % (self.class_identifier, prop, params[0]))
        setattr(target, prop, params[0])

    def _get_property(self, target, prop, params: Optional[Tuple] = ()) -> Tuple[Any]:
        try:
            value = getattr(target, prop)
        except RuntimeError:
            #--------------------------------------------------------------------------------
            # Gracefully handle errors, which may occur when querying parameters that don't apply
            # to a particular object (e.g. track.fold_state for a non-group track)
            #--------------------------------------------------------------------------------
            value = None
        self.logger.info("Getting property for %s: %s = %s" % (self.class_identifier, prop, value))
        return value,

    def _start_listen(self, target, prop, params: Optional[Tuple] = ()) -> None:
        """
        Start listening for the property named `prop` on the Live object `target`.
        `params` is typically a tuple containing the track/clip index.

        Args:
            target: 
            prop:
            params:
        """
        def property_changed_callback():
            try:
                value = getattr(target, prop)
                self.logger.info("Property %s changed of %s %s: %s" % (prop, self.class_identifier, str(params), value))
                osc_address = "/live/%s/get/%s" % (self.class_identifier, prop)
                self.osc_server.send(osc_address, (*params, value,))
            except Exception as e:
                self.logger.warning(f"Error in property_changed_callback for {prop}: {e}")

        listener_key = (prop, tuple(params))
        
        # Remove existing listener if present
        if listener_key in self.listener_functions:
            self._stop_listen(target, prop, params)

        try:
            self.logger.info("Adding listener for %s %s, property: %s" % (self.class_identifier, str(params), prop))
            add_listener_function_name = "add_%s_listener" % prop
            add_listener_function = getattr(target, add_listener_function_name)
            add_listener_function(property_changed_callback)
            self.listener_functions[listener_key] = property_changed_callback
            
            # Immediately send the current value
            property_changed_callback()
        except AttributeError as e:
            self.logger.warning(f"Cannot add listener for {prop}: {e}")
            raise

    def _stop_listen(self, target, prop, params: Optional[Tuple[Any]] = ()) -> None:
        listener_key = (prop, tuple(params))
        if listener_key in self.listener_functions:
            self.logger.info("Removing listener for %s %s, property %s" % (self.class_identifier, str(params), prop))
            listener_function = self.listener_functions[listener_key]
            try:
                remove_listener_function_name = "remove_%s_listener" % prop
                remove_listener_function = getattr(target, remove_listener_function_name)
                remove_listener_function(listener_function)
                del self.listener_functions[listener_key]
            except AttributeError as e:
                self.logger.warning(f"Cannot remove listener for {prop}: {e}")
                # Still remove from our tracking
                del self.listener_functions[listener_key]
        else:
            self.logger.warning("No listener function found for property: %s (%s)" % (prop, str(params)))