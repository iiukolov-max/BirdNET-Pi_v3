# Applying Settings

Update Settings applies only changed values. Saving an unchanged form does not
create a background job or restart services.

| Change | Application |
|---|---|
| Station name, image options, update options, cleanup limits | Saved immediately; used by the next relevant request or cleanup |
| Notifications, BirdWeather ID, remote batch size | Saved immediately; refreshed by the running consumer between operations |
| Models, geographic filtering, audio input, recording mode | Applied in the background when running services must change |
| Optional service permission | Only the affected service; saved immediately when the current mode already prevents it from running |
| Web access / streaming server credentials | Applied in the background with configuration checks and rollback |

Maximum disk usage is picked up by archive recording during its next disk check,
approximately every ten seconds; changing it does not restart recording.
Changes to model/capture settings retain their existing transaction and recovery
behavior. Failed saves restore the button and screen. A form opened before another
configuration change must be reloaded before saving.

Spectrograms load from the top of the recording list down, one expensive image
request at a time. Audio does not wait for the image queue. New frequency-shift
settings use a separate derived-audio cache. Existing source recordings are not
rewritten; existing spectrogram PNGs are not automatically regenerated.

Some changes need functioning hardware or a reachable analysis PC to become
ready. These waits apply to the relevant background operation, not to unrelated
display or cleanup changes.
