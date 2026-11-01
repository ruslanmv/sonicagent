/** Apply server events to the playback clock. Binary frames are not decoded here. */

import { PlaybackClock } from "../audio/playback";

export interface ControlEvent {
  type: string;
  clear_audio?: boolean;
}

export function applyControlEvent(clock: PlaybackClock, event: ControlEvent): void {
  if (event.type === "response.cancelled" && event.clear_audio) clock.clear();
}
