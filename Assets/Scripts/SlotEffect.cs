using UnityEngine;

/// <summary>
/// Base class for slot particle + audio effects (used by SlotNew and SlotSell).
/// </summary>
public class SlotEffect : MonoBehaviour
{
    ParticleSystem particleVFX;
    AudioSource audioSource;

    void Start()
    {
        particleVFX = GetComponentInChildren<ParticleSystem>();
        audioSource = GetComponentInChildren<AudioSource>();
    }

    public void PlayEffect()
    {
        if (particleVFX)
        {
            particleVFX.Play();
            audioSource.Play();
        }
    }
}
