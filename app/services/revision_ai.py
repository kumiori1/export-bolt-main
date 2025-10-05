import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def compare_scenes_for_changes(original_scenes: List[Dict], revised_scenes: List[Dict]) -> List[Dict]:
    """
    Compare original and revised scenes to determine which assets need regeneration
    
    Args:
        original_scenes: List of original scene dictionaries from database
        revised_scenes: List of revised scene dictionaries from GPT-4
        
    Returns:
        List of scene change dictionaries with regeneration flags and URLs
    """
    try:
        logger.info("REVISION_COMPARE: Starting scene comparison for granular regeneration...")
        logger.info(f"REVISION_COMPARE: Comparing {len(original_scenes)} original scenes with {len(revised_scenes)} revised scenes")
        
        scene_changes = []
        
        # Create lookup maps for easier comparison
        original_map = {scene.get("scene_number", i+1): scene for i, scene in enumerate(original_scenes)}
        revised_map = {scene.get("scene_number", i+1): scene for i, scene in enumerate(revised_scenes)}
        
        # Compare each scene
        for scene_number in range(1, len(revised_scenes) + 1):
            original_scene = original_map.get(scene_number, {})
            revised_scene = revised_map.get(scene_number, {})
            
            if not original_scene or not revised_scene:
                logger.warning(f"REVISION_COMPARE: Missing scene {scene_number} in original or revised data")
                continue
            
            # Extract prompts for comparison
            original_image_prompt = original_scene.get("image_prompt", "").strip()
            revised_image_prompt = revised_scene.get("image_prompt", "").strip()
            
            original_voiceover_prompt = original_scene.get("vioce_over", "").strip()
            revised_voiceover_prompt = revised_scene.get("vioce_over", "").strip()
            
            # Extract voice settings for comparison
            original_emotion = original_scene.get("eleven_labs_emotion", "neutral").strip()
            revised_emotion = revised_scene.get("eleven_labs_emotion", "neutral").strip()
            
            original_voice_id = original_scene.get("eleven_labs_voice_id", "Wise_Woman").strip()
            revised_voice_id = revised_scene.get("eleven_labs_voice_id", "Wise_Woman").strip()
            
            original_video_prompt = original_scene.get("visual_description", "").strip()
            revised_video_prompt = revised_scene.get("visual_description", "").strip()
            
            # Determine what needs regeneration
            image_needs_regen = original_image_prompt != revised_image_prompt
            voiceover_needs_regen = (
                original_voiceover_prompt != revised_voiceover_prompt or
                original_emotion != revised_emotion or
                original_voice_id != revised_voice_id
            )
            
            # Video needs regeneration if either the video prompt OR the image prompt changed
            # (since video is generated from the image)
            video_needs_regen = (original_video_prompt != revised_video_prompt) or image_needs_regen
            
            # Get original asset URLs
            original_image_url = original_scene.get("image_url", "")
            original_voiceover_url = original_scene.get("voiceover_url", "")
            original_video_url = original_scene.get("scene_clip_url", "")
            
            scene_change = {
                "scene_number": scene_number,
                "image_needs_regen": image_needs_regen,
                "voiceover_needs_regen": voiceover_needs_regen,
                "video_needs_regen": video_needs_regen,
                "original_image_url": original_image_url,
                "original_voiceover_url": original_voiceover_url,
                "original_video_url": original_video_url,
                "revised_image_prompt": revised_image_prompt,
                "revised_voiceover_prompt": revised_voiceover_prompt,
                "revised_emotion": revised_emotion,
                "revised_voice_id": revised_voice_id,
                "revised_video_prompt": revised_video_prompt
            }
            
            scene_changes.append(scene_change)
            
            # Log what needs regeneration for this scene
            regen_items = []
            if image_needs_regen:
                regen_items.append("image")
            if voiceover_needs_regen:
                regen_items.append("voiceover")
                if original_emotion != revised_emotion:
                    logger.info(f"REVISION_COMPARE: Scene {scene_number} emotion changed: {original_emotion} → {revised_emotion}")
                if original_voice_id != revised_voice_id:
                    logger.info(f"REVISION_COMPARE: Scene {scene_number} voice changed: {original_voice_id} → {revised_voice_id}")
            if video_needs_regen:
                regen_items.append("video")
            
            if regen_items:
                logger.info(f"REVISION_COMPARE: Scene {scene_number} needs regeneration: {', '.join(regen_items)}")
            else:
                logger.info(f"REVISION_COMPARE: Scene {scene_number} unchanged - reusing all assets")
        
        # Summary statistics
        total_images_to_regen = sum(1 for sc in scene_changes if sc["image_needs_regen"])
        total_voiceovers_to_regen = sum(1 for sc in scene_changes if sc["voiceover_needs_regen"])
        total_videos_to_regen = sum(1 for sc in scene_changes if sc["video_needs_regen"])
        
        logger.info(f"REVISION_COMPARE: Regeneration summary:")
        logger.info(f"REVISION_COMPARE: - Images: {total_images_to_regen}/{len(scene_changes)} scenes")
        logger.info(f"REVISION_COMPARE: - Voiceovers: {total_voiceovers_to_regen}/{len(scene_changes)} scenes")
        logger.info(f"REVISION_COMPARE: - Videos: {total_videos_to_regen}/{len(scene_changes)} scenes")
        
        return scene_changes
        
    except Exception as e:
        logger.error(f"REVISION_COMPARE: Failed to compare scenes: {e}")
        logger.exception("Full traceback:")
        return []


async def generate_revised_wan_scenes_with_gpt4(
    revision_request: str, 
    original_scenes: List[Dict], 
    openai_client: AsyncOpenAI
) -> List[Dict[str, Any]]:
    """
    Generate revised WAN scenes using GPT-4 based on user revision request and original WAN scenes
    
    Args:
        revision_request: User's natural language revision request
        original_scenes: List of 6 original WAN scene dictionaries from database
        openai_client: OpenAI client instance
        
    Returns:
        List of 6 revised WAN scene dictionaries with updated fields
    """
    try:
        logger.info("WAN_REVISION_AI: Starting WAN scene revision with GPT-4...")
        logger.info(f"WAN_REVISION_AI: Revision request: {revision_request[:100]}...")
        logger.info(f"WAN_REVISION_AI: Processing {len(original_scenes)} original WAN scenes")

        # Check if revision request mentions missing music
        revision_lower = revision_request.lower()
        music_missing_keywords = ["no music", "no background music", "missing music", "add music", "needs music", "without music", "no sound", "silent"]
        mentions_missing_music = any(keyword in revision_lower for keyword in music_missing_keywords)
        
        if mentions_missing_music:
            logger.info("WAN_REVISION_AI: User mentions missing music - will trigger music generation")
        # Prepare original WAN scenes data for GPT-4 (map database fields back to WAN format)
        wan_scenes_for_ai = []
        for scene in original_scenes:
            wan_scene_data = {
                "scene_number": scene.get("scene_number", 1),
                "nano_banana_prompt": scene.get("image_prompt", ""),  # Map back from image_prompt
                "elevenlabs_prompt": scene.get("vioce_over", ""),     # Map back from vioce_over
                "eleven_labs_emotion": scene.get("eleven_labs_emotion", "neutral"),  # Include emotion
                "eleven_labs_voice_id": scene.get("eleven_labs_voice_id", "Wise_Woman"),  # Include voice ID
                "wan2_5_prompt": scene.get("visual_description", "") # Map back from visual_description
            }
            wan_scenes_for_ai.append(wan_scene_data)
            logger.info(f"WAN_REVISION_AI: Original WAN Scene {wan_scene_data['scene_number']}: {wan_scene_data['nano_banana_prompt'][:50]}...")
            logger.info(f"WAN_REVISION_AI: Original WAN Scene {wan_scene_data['scene_number']} - Voice: {wan_scene_data['eleven_labs_voice_id']}, Emotion: {wan_scene_data['eleven_labs_emotion']}")

        system_prompt = """You are an expert AI WAN video revision specialist that processes user revision requests with surgical precision for WAN 2.5 workflow.

CRITICAL WAN DATABASE FIELD MAPPING:
- nano_banana_prompt: Image generation prompt for Nano Banana (stored as image_prompt in DB)
- elevenlabs_prompt: Voice generation prompt for ElevenLabs (stored as vioce_over in DB)
- eleven_labs_emotion: Emotion for voiceover generation (stored as eleven_labs_emotion in DB)
- eleven_labs_voice_id: Voice ID for voiceover generation (stored as eleven_labs_voice_id in DB)
- wan2_5_prompt: Video animation prompt for WAN 2.5 (stored as visual_description in DB)

VOICE AND EMOTION CONSTRAINTS:
- eleven_labs_emotion MUST be one of: ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
- eleven_labs_voice_id MUST be one of: ["Deep_Voice_Man", "Wise_Woman"]
- PRESERVE original voice_id and emotion unless user explicitly requests a change
- If user says they don't like the voice, suggest the available voice options
- If user mentions emotion changes, use the allowed emotion list

MUSIC HANDLING INTELLIGENCE (ENHANCED):
- If user mentions "no music", "missing music", "add music", "needs music", "without music", "no sound", "silent", "quiet", "muted" → AUTOMATICALLY generate new background music
- Music generation uses a default prompt: "Lo-fi hip-hop with a light upbeat rhythm, soft percussion, and a steady background flow. Casual and positive, perfect for maintaining a smooth ad vibe across all scenes, ending gently at the final call-to-action."
- This is handled OUTSIDE of scene-level prompts (music is video-wide, not scene-specific)

WAN REVISION ANALYSIS PROTOCOL:

1. DETECT & PRIORITIZE ISSUES (NEW):
   - Keywords like "bug", "error", "looks weird", "unnatural", "bent", "glitch", "not right", "awkward", "stiff", "distorted", "unrealistic", "broken", "messed up" indicate a PROBLEM with previous AI generation
   - When detected, PRIORITIZE fixing the problem over adding new creative elements
   - Understand that visual issues might require adjustments to BOTH nano_banana_prompt AND wan2_5_prompt for complete fixes

2. PARSE USER INTENT with extreme precision for WAN workflow:
   - "image", "background", "lighting", "scene", "visual", "appearance" → ONLY nano_banana_prompt
   - "voice", "speech", "narration", "dialogue", "says", "talks" → ONLY elevenlabs_prompt
   - "voice change", "different voice", "don't like voice", "change speaker" → ONLY eleven_labs_voice_id (suggest available options)
   - "emotion", "tone", "feeling", "mood of voice", "sound more", "less energetic" → ONLY eleven_labs_emotion
   - "movement", "motion", "action", "camera", "animation", "video" → ONLY wan2_5_prompt
   - Scene numbers (1-6) → Target ONLY that specific scene
   - "all scenes", "entire video", "everything" → Apply to ALL 6 scenes

3. FIELD PRESERVATION RULE (REFINED):
   - If a field is NOT mentioned in the revision request → Return EXACT original value
   - ESPECIALLY preserve eleven_labs_voice_id and eleven_labs_emotion unless explicitly mentioned
   - If a field IS mentioned → Update according to user's specific request
   - EXCEPTION: If a quality issue is detected, proactively improve relevant prompts to fix the issue
   - MINIMAL NECESSARY CHANGE: Only make the minimum required adjustments to fulfill the request and fix identified issues

4. SMART CONTENT MATCHING (CRITICAL):
   - When user describes content without scene numbers, search ALL scenes
   - Match user descriptions to existing nano_banana_prompt, elevenlabs_prompt, or wan2_5_prompt content
   - Example: "the woman walking" should find scene with woman walking in nano_banana_prompt or wan2_5_prompt
   - Be intelligent about partial matches: "man running bent" should match scenes with "man running" even if "bent" isn't explicitly mentioned
   - Consider synonyms and related terms: "person" = "man/woman", "moving" = "walking/running", etc.

5. CHANGE SCOPE DETECTION:
   - SPECIFIC: "change scene 3's background" → Only scene 3, only nano_banana_prompt
   - GLOBAL: "make all voices more energetic" → All 6 scenes, only elevenlabs_prompt
   - VOICE SPECIFIC: "use a different voice" → All 6 scenes, only eleven_labs_voice_id (suggest options)
   - TARGETED: "the woman should move slower" → Find scene with woman, update ONLY wan2_5_prompt

6. WAN-SPECIFIC INTELLIGENCE (ENHANCED):
   - Understand that nano_banana_prompt creates the static image
     * Should contain: objects, people, setting, lighting, camera style, composition
     * Should NOT contain: motion, animation, transitions, or temporal elements
   - Understand that wan2_5_prompt animates that static image
     * Should contain: motion, animation, camera movement, transitions, SFX, temporal changes
     * Should NOT contain: static visual descriptions (those belong in nano_banana_prompt)
   - Understand that elevenlabs_prompt creates the voiceover
     * Should contain: spoken dialogue, narration text, delivery style
   - Understand that eleven_labs_emotion and eleven_labs_voice_id control voice characteristics
     * Must use exact values from allowed lists
     * Should remain consistent unless user requests changes
   - Keep prompts concise and AI-model-friendly
   - Maintain UGC aesthetic and low-fi style
   - When fixing quality issues, add specific guidance to prevent the problem from recurring

7. QUALITY ASSURANCE & PROBLEM SOLVING (NEW):
   - If user reports a visual problem (e.g., "bent", "distorted", "unnatural pose"), enhance nano_banana_prompt with corrective guidance
   - If user reports a motion problem (e.g., "stiff movement", "awkward animation"), enhance wan2_5_prompt with corrective guidance
   - Add positive constraints: "natural posture", "fluid movement", "realistic proportions"
   - Add negative constraints: "no distortion", "no awkward bending", "no stiff animation"
   - Example: For "man running bent" → Update wan2_5_prompt to include "natural running motion, fluid movement, no distortion, realistic posture"
FORBIDDEN BEHAVIORS:
8. VOICE AND EMOTION HANDLING:
   - If user expresses dissatisfaction with voice: "Available voices are Deep_Voice_Man and Wise_Woman. Which would you prefer?"
   - If user requests emotion change: Use exact emotion from ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
   - Maintain voice consistency across all 6 scenes unless user specifies different voices for different scenes
   - Preserve original voice settings if not mentioned in revision request
- NEVER change unmentioned fields "for consistency"
- NEVER make "improvements" not requested by user
- NEVER assume related changes across different prompt types
- NEVER modify scene_number values
- NEVER make prompts overly complex or lengthy
- NEVER introduce new visual elements, characters, or objects not present in the original scene or explicitly requested
- NEVER make changes that contradict the core product or message of the video
- NEVER use voice_id or emotion values outside the allowed lists
- NEVER change voice settings without user request

OUTPUT REQUIREMENTS:
- Always include all 3 fields for each scene: nano_banana_prompt, elevenlabs_prompt, wan2_5_prompt
- Preserve original values for unchanged fields EXACTLY (no paraphrasing)
- Only modify fields explicitly or implicitly targeted by the revision request
- Keep all prompts concise and AI-model-friendly

EXAMPLE MAPPINGS:
- "make the character move slower" → Find scene with character, update ONLY wan2_5_prompt
- "add more camera movement to scene 2" → Scene 2 only, update ONLY wan2_5_prompt

Output format (JSON only, no explanations or markdown):
{
  "scenes": [
    {
      "scene_number": 1,
      "nano_banana_prompt": "...",
      "elevenlabs_prompt": "...",
      "eleven_labs_emotion": "...",
      "eleven_labs_voice_id": "...",
      "wan2_5_prompt": "..."
    },
    ...
  ]
}"""

        # Prepare the user message with revision request and original WAN scenes
        user_message = f"""WAN REVISION REQUEST: {revision_request}

ORIGINAL WAN SCENES:
{json.dumps(wan_scenes_for_ai, indent=2)}

INSTRUCTIONS:
1. Analyze the WAN revision request with surgical precision
2. Identify EXACTLY which WAN prompt fields need changes based on the request
3. For unchanged fields, return the EXACT original values (no paraphrasing)
4. For changed fields, implement the user's specific request while keeping prompts concise
5. Return complete JSON with all 6 WAN scenes and all 3 fields per scene"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        logger.info("WAN_REVISION_AI: Sending WAN revision request to GPT-4...")
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=3000,
            temperature=0.7
        )

        logger.info("WAN_REVISION_AI: Response received from GPT-4")
        content = response.choices[0].message.content

        if not content:
            logger.error("WAN_REVISION_AI: Empty response from GPT-4")
            return []

        logger.info(f"WAN_REVISION_AI: Response content length: {len(content)} characters")
        logger.info(f"WAN_REVISION_AI: Raw response: {content[:200]}...")

        # Parse JSON response
        logger.info("WAN_REVISION_AI: Parsing WAN JSON response...")

        # Clean the response - remove any markdown formatting
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        if not content:
            logger.error("WAN_REVISION_AI: Content is empty after cleaning")
            return []

        # Parse the JSON response
        parsed_response = json.loads(content)
        
        # Extract scenes array from the response
        if isinstance(parsed_response, dict) and "scenes" in parsed_response:
            revised_wan_scenes = parsed_response["scenes"]
        elif isinstance(parsed_response, list):
            # Fallback: if it's directly an array
            revised_wan_scenes = parsed_response
        else:
            logger.error(f"WAN_REVISION_AI: Unexpected response format: {type(parsed_response)}")
            return []

        if not isinstance(revised_wan_scenes, list) or len(revised_wan_scenes) != 6:
            logger.error(
                f"WAN_REVISION_AI: Invalid response format - expected 6 WAN scenes, got {len(revised_wan_scenes) if isinstance(revised_wan_scenes, list) else 'non-list'}")
            return []

        # Validate each WAN scene has required fields
        for i, scene in enumerate(revised_wan_scenes):
            required_fields = ["scene_number", "nano_banana_prompt", "elevenlabs_prompt", "eleven_labs_emotion", "eleven_labs_voice_id", "wan2_5_prompt"]
            for field in required_fields:
                if field not in scene:
                    logger.error(f"WAN_REVISION_AI: WAN Scene {i+1} missing required field: {field}")
                    return []

        # Convert WAN scenes back to database format for storage
        database_format_scenes = []
        for wan_scene in revised_wan_scenes:
            db_scene = {
                "scene_number": wan_scene.get("scene_number", 1),
                "image_prompt": wan_scene.get("nano_banana_prompt", ""),     # Map to image_prompt
                "visual_description": wan_scene.get("wan2_5_prompt", ""),   # Map to visual_description
                "vioce_over": wan_scene.get("elevenlabs_prompt", ""),       # Map to vioce_over
                "eleven_labs_emotion": wan_scene.get("eleven_labs_emotion", "neutral"),  # Map emotion
                "eleven_labs_voice_id": wan_scene.get("eleven_labs_voice_id", "Wise_Woman"),  # Map voice ID
                "sound_effects": "",  # WAN workflow doesn't use separate sound effects
                "music_direction": "" # WAN workflow doesn't use separate music direction
            }
            database_format_scenes.append(db_scene)

        logger.info(f"WAN_REVISION_AI: Successfully generated {len(database_format_scenes)} revised WAN scenes!")
        for i, scene in enumerate(database_format_scenes, 1):
            nano_prompt = scene.get('image_prompt', '')[:50] + "..."
            logger.info(f"WAN_REVISION_AI: Revised WAN Scene {i}: {nano_prompt}")
            logger.info(f"WAN_REVISION_AI: Revised WAN Scene {i} - Voice: {scene.get('eleven_labs_voice_id')}, Emotion: {scene.get('eleven_labs_emotion')}")

        # Return both scenes and music generation flag
        return database_format_scenes, mentions_missing_music

    except json.JSONDecodeError as e:
        logger.error(f"WAN_REVISION_AI: JSON parsing failed: {e}")
        logger.error(f"WAN_REVISION_AI: Content that failed to parse: '{content}'")
        return []
    except Exception as e:
        logger.error(f"WAN_REVISION_AI: Failed to generate revised WAN scenes: {e}")
        logger.exception("Full traceback:")
        return []
async def generate_revised_scenes_with_gpt4(
    revision_request: str, 
    original_scenes: List[Dict], 
    openai_client: AsyncOpenAI
) -> List[Dict[str, Any]]:
    """
    Generate revised scenes using GPT-4 based on user revision request and original scenes
    
    Args:
        revision_request: User's natural language revision request
        original_scenes: List of 5 original scene dictionaries from database
        openai_client: OpenAI client instance
        
    Returns:
        List of 5 revised scene dictionaries with updated fields
    """
    try:
        logger.info("REVISION_AI: Starting scene revision with GPT-4...")
        logger.info(f"REVISION_AI: Revision request: {revision_request[:100]}...")
        logger.info(f"REVISION_AI: Processing {len(original_scenes)} original scenes")

        # Prepare original scenes data for GPT-4
        scenes_for_ai = []
        for scene in original_scenes:
            scene_data = {
                "scene_number": scene.get("scene_number", 1),
                "image_prompt": scene.get("image_prompt", ""),
                "visual_description": scene.get("visual_description", ""),
                "vioce_over": scene.get("vioce_over", ""),  # Fixed: use correct field name
                "sound_effects": scene.get("sound_effects", ""),
                "music_direction": scene.get("music_direction", "")
            }
            scenes_for_ai.append(scene_data)
            logger.info(f"REVISION_AI: Original Scene {scene_data['scene_number']}: {scene_data['visual_description'][:50]}...")

        system_prompt = """You are an expert AI video revision specialist that processes user revision requests with surgical precision.

CRITICAL DATABASE FIELD MAPPING:
- image_prompt: Combined image generation prompt
- visual_description: Video motion and visual elements
- voiceover: Spoken dialogue/narration text
- vioce_over: Spoken dialogue/narration text
- sound_effects: Audio effects and ambient sounds
- music_direction: Background music style and mood

REVISION ANALYSIS PROTOCOL:

1. PARSE USER INTENT with extreme precision:
   - "movement", "motion", "action", "camera" → ONLY visual_description
   - "background", "lighting", "scene", "visual" → ONLY visual_description + image_prompt
   - "dialogue", "speech", "narration", "voice", "says" → ONLY vioce_over
   - "music", "soundtrack", "background music" → ONLY music_direction
   - "sound", "audio effects", "ambient" → ONLY sound_effects
   - Scene numbers (1-5) → Target ONLY that specific scene
   - "all scenes", "entire video", "everything" → Apply to ALL scenes

2. FIELD PRESERVATION RULE:
   - If a field is NOT mentioned in the revision request → Return EXACT original value
   - If a field IS mentioned → Update according to user's specific request
   - NEVER make assumptions or "helpful" changes to unmentioned fields

3. SMART CONTENT MATCHING:
   - When user describes content without scene numbers, search ALL scenes
   - Match user descriptions to existing visual_description or voiceover content
   - Example: "the woman walking" should find scene with woman walking in visual_description

4. CHANGE SCOPE DETECTION:
   - SPECIFIC: "change scene 3's background" → Only scene 3, only visual_description + image_prompt
   - GLOBAL: "make the music more dramatic" → All 5 scenes, only music_direction
   - TARGETED: "the woman should say something different" → Find scene with woman, update ONLY vioce_over

FORBIDDEN BEHAVIORS:
- NEVER change unmentioned fields "for consistency"
- NEVER make "improvements" not requested by user
- NEVER assume related changes (e.g., changing music when user asks for visual changes)
- NEVER modify scene_number values

OUTPUT REQUIREMENTS:
- Always return exactly 5 scenes
- Always include all 5 fields for each scene: image_prompt, visual_description, voiceover, sound_effects, music_direction
- Always include all 5 fields for each scene: image_prompt, visual_description, vioce_over, sound_effects, music_direction
- Preserve original values for unchanged fields EXACTLY (no paraphrasing)
- Only modify fields explicitly or implicitly targeted by the revision request

EXAMPLE MAPPINGS:
- "make the character move slower" → Find scene with character movement, update ONLY visual_description
- "change the background music to jazz" → Update ONLY music_direction in ALL 5 scenes
- "the woman should say something different" → Find scene with woman, update ONLY voiceover
- "the woman should say something different" → Find scene with woman, update ONLY vioce_over
- "add more lighting to scene 2" → Scene 2 only, update ONLY visual_description + image_prompt
- "remove the sound effects" → Update ONLY sound_effects in ALL 5 scenes to empty or minimal

Output format (JSON only, no explanations or markdown):
{
  "scenes": [
    {
      "scene_number": 1,
      "image_prompt": "...",
      "visual_description": "...",
     "vioce_over": "...",
      "sound_effects": "...",
      "music_direction": "..."
    },
    ...
  ]
}"""

        # Prepare the user message with revision request and original scenes
        user_message = f"""REVISION REQUEST: {revision_request}

ORIGINAL SCENES:
{json.dumps(scenes_for_ai, indent=2)}

INSTRUCTIONS:
1. Analyze the revision request with surgical precision
2. Identify EXACTLY which fields need changes based on the request
3. For unchanged fields, return the EXACT original values (no paraphrasing)
4. For changed fields, implement the user's specific request
5. Return complete JSON with all 5 scenes and all 5 fields per scene"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        logger.info("REVISION_AI: Sending revision request to GPT-4...")
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2500,
            temperature=0.7
        )

        logger.info("REVISION_AI: Response received from GPT-4")
        content = response.choices[0].message.content

        if not content:
            logger.error("REVISION_AI: Empty response from GPT-4")
            return []

        logger.info(f"REVISION_AI: Response content length: {len(content)} characters")
        logger.info(f"REVISION_AI: Raw response: {content[:200]}...")

        # Parse JSON response
        logger.info("REVISION_AI: Parsing JSON response...")

        # Clean the response - remove any markdown formatting
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        if not content:
            logger.error("REVISION_AI: Content is empty after cleaning")
            return []

        # Parse the JSON response
        parsed_response = json.loads(content)
        
        # Extract scenes array from the response
        if isinstance(parsed_response, dict) and "scenes" in parsed_response:
            revised_scenes = parsed_response["scenes"]
        elif isinstance(parsed_response, list):
            # Fallback: if it's directly an array
            revised_scenes = parsed_response
        else:
            logger.error(f"REVISION_AI: Unexpected response format: {type(parsed_response)}")
            return []

        if not isinstance(revised_scenes, list) or len(revised_scenes) != 5:
            logger.error(
                f"REVISION_AI: Invalid response format - expected 5 scenes, got {len(revised_scenes) if isinstance(revised_scenes, list) else 'non-list'}")
            return []

        # Validate each scene has required fields
        for i, scene in enumerate(revised_scenes):
            required_fields = ["scene_number", "image_prompt", "visual_description", "vioce_over", "sound_effects", "music_direction"]
            for field in required_fields:
                if field not in scene:
                    logger.error(f"REVISION_AI: Scene {i+1} missing required field: {field}")
                    return []

        logger.info(f"REVISION_AI: Successfully generated {len(revised_scenes)} revised scenes!")
        for i, scene in enumerate(revised_scenes, 1):
            visual_desc = scene.get('visual_description', '')[:50] + "..."
            logger.info(f"REVISION_AI: Revised Scene {i}: {visual_desc}")

        return revised_scenes

    except json.JSONDecodeError as e:
        logger.error(f"REVISION_AI: JSON parsing failed: {e}")
        logger.error(f"REVISION_AI: Content that failed to parse: '{content}'")
        return []
    except Exception as e:
        logger.error(f"REVISION_AI: Failed to generate revised scenes: {e}")
        logger.exception("Full traceback:")
        return []