# TouchOSC Hanging Debug Branch

This branch contains debugging modifications to help identify why Ableton hangs when TouchOSC connects, particularly when switching from editor to run mode.

## Changes Made

### 1. Enhanced OSC Message Logging (`osc_server.py`)
- Added detailed logging for all incoming OSC messages
- Special tracking for "listen" messages with timestamps
- Monitoring for slow callbacks (>100ms)
- Wildcard match counting
- Message rate tracking

### 2. Listener Registration Debugging (`handler.py`)
- Added rate limiting (5ms between listener registrations)
- Tracking total listener count
- Logging active listener count with each registration
- Debug messages for listener lifecycle

### 3. Threading Locks Disabled (`track.py`)
- **TEMPORARILY DISABLED** all threading locks in track listener methods
- This helps identify if the threading implementation is causing deadlocks
- All `with self._listener_lock:` statements are commented out

## How to Use This Debug Branch

1. **Check out this branch in your AbletonOSC fork:**
   ```
   git fetch origin
   git checkout debug/touchosc-hanging-issue
   ```

2. **Monitor the logs:**
   - The log file is typically at: `[AbletonOSC directory]/logs/abletonosc.log`
   - On macOS: `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/logs/abletonosc.log`
   - On Windows: `\Users\[username]\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\logs\abletonosc.log`

3. **Reproduce the issue:**
   - Start Ableton with a simple project
   - Open TouchOSC in editor mode
   - Switch to run mode
   - Watch for hanging

4. **What to look for in logs:**
   - `[DEBUG] LISTENER MSG` - Shows all listener registration attempts
   - `[DEBUG] SLOW CALLBACK` - Indicates performance issues
   - `[DEBUG] Rate limiting` - Shows if rate limiter is triggered
   - `TOO MANY REPEATS` - Indicates message flooding
   - Error messages about failed listener registration

5. **If hanging is resolved:**
   - The threading locks were the issue
   - We need a better threading strategy

6. **If hanging persists:**
   - Check logs for patterns:
     - How many listeners are created?
     - Which specific listeners fail?
     - Is there a specific message that triggers the hang?

## Debug Flags

You can modify these in the code:

- `osc_server.py`: `self.debug_touchosc = True/False` (line 45)
- `handler.py`: `self._listener_rate_limit = 0.005` (adjust rate limit in seconds)

## Next Steps Based on Results

1. **If threading was the issue:**
   - Implement lock-free listener management
   - Use queue-based approach
   - Add timeout to locks

2. **If message flooding:**
   - Implement message batching
   - Add debouncing for rapid listener creation
   - Limit concurrent listener registrations

3. **If specific message pattern:**
   - Add filtering for problematic messages
   - Implement selective listener registration

## Reporting Results

Please share:
1. The last 100-200 lines of the log before hanging
2. Whether disabling threading fixed the issue
3. Total message count before hanging
4. Any error messages

This will help identify the root cause and implement a proper fix.
