# AbletonOSC Return Track Support

This fork adds comprehensive return track support to AbletonOSC, enabling full control over Ableton Live's return tracks via OSC.

## New Features

### Song-level Return Track Queries

- `/live/song/get/num_return_tracks` - Get the number of return tracks
- `/live/song/get/return_track_names` - Get return track names  
- `/live/song/get/return_track_data` - Get detailed return track data

### Return Track Control (/live/return/)

All return track operations use the `/live/return/` namespace with the same patterns as regular tracks:

#### Properties (Read/Write)
- `/live/return/get/name <index>` - Get return track name
- `/live/return/set/name <index> <name>` - Set return track name
- `/live/return/get/color <index>` - Get return track color
- `/live/return/set/color <index> <color>` - Set return track color
- `/live/return/get/mute <index>` - Get mute state
- `/live/return/set/mute <index> <0/1>` - Set mute state
- `/live/return/get/solo <index>` - Get solo state
- `/live/return/set/solo <index> <0/1>` - Set solo state

#### Mixer Controls
- `/live/return/get/volume <index>` - Get return track volume
- `/live/return/set/volume <index> <value>` - Set return track volume (0.0-1.0)
- `/live/return/get/panning <index>` - Get return track panning
- `/live/return/set/panning <index> <value>` - Set return track panning (-1.0 to 1.0)

#### Send Controls
- `/live/return/get/send <index> <send_id>` - Get send value
- `/live/return/set/send <index> <send_id> <value>` - Set send value

#### Device Controls
- `/live/return/get/num_devices <index>` - Get number of devices
- `/live/return/get/devices/name <index>` - Get device names
- `/live/return/get/devices/type <index>` - Get device types
- `/live/return/get/devices/class_name <index>` - Get device class names

#### Clip Controls
- `/live/return/get/clips/name <index>` - Get clip names
- `/live/return/get/clips/length <index>` - Get clip lengths
- `/live/return/delete_clip <index> <clip_slot>` - Delete a clip

#### Metering
- `/live/return/get/output_meter_level <index>` - Get output meter level
- `/live/return/get/output_meter_left <index>` - Get left channel meter
- `/live/return/get/output_meter_right <index>` - Get right channel meter

#### Output Routing
- `/live/return/get/output_routing_type <index>` - Get output routing type
- `/live/return/set/output_routing_type <index> <type>` - Set output routing type
- `/live/return/get/output_routing_channel <index>` - Get output routing channel
- `/live/return/set/output_routing_channel <index> <channel>` - Set output routing channel

## Usage Examples

### TouchOSC Example

To control the first return track's volume:
```
# Get current volume
/live/return/get/volume 0

# Set volume to 75%
/live/return/set/volume 0 0.75

# Mute the return track
/live/return/set/mute 0 1
```

### Getting All Return Tracks
```python
# Get number of return tracks
send("/live/song/get/num_return_tracks")

# Get all return track names
send("/live/song/get/return_track_names")
```

## Implementation Details

The implementation follows the same patterns as regular tracks but uses the dedicated `/live/return/` namespace. Return tracks are indexed starting from 0, independent of regular track indices.

## Compatibility

This fork maintains full backward compatibility with the original AbletonOSC. All existing functionality remains unchanged - this only adds new features for return track support.

## Installation

1. Replace your existing AbletonOSC installation with this fork
2. Restart Ableton Live
3. The new return track endpoints will be immediately available

## Testing

The implementation has been tested with:
- Ableton Live 11
- Multiple return tracks
- Various device configurations
- TouchOSC templates

## Contributing

Feel free to report issues or submit pull requests for additional return track functionality.
