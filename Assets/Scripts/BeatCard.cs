using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class BeatCard : MonoBehaviour
{
    [SerializeField] bool activated = false;

    BeatGenerator beatGenerator;
    SpriteRenderer noteRenderer;
    SpriteRenderer boxRenderer;
    CardFrame cardFrameAttached;
    Card cardAttached;
    ManaDisplay manaDisplay;
    float manaReductionMultiplier;
    float manaIncreaseMultiplier1;
    float manaIncreaseMultiplier2;
    float manaIncreaseMultiplier3;
    string modeBeat = "double";
    float timeBeat;


    void Start()
    {
        SpriteRenderer[] spriteRenderers = GetComponentsInChildren<SpriteRenderer>();
        foreach(SpriteRenderer spriteIter in spriteRenderers)
        {
            if(spriteIter.gameObject.name == "Beat Box")
            {
                boxRenderer = spriteIter; 
                boxRenderer.gameObject.SetActive(false);
            }
            else if(spriteIter.gameObject.name == "Note Drawing")
            {
                noteRenderer = spriteIter;
                noteRenderer.gameObject.SetActive(false);
            }
        }
        
        manaDisplay = FindAnyObjectByType<ManaDisplay>();
        beatGenerator = FindAnyObjectByType<BeatGenerator>();
        manaReductionMultiplier = manaDisplay.manaReductionMultiplier;
        manaIncreaseMultiplier1 = manaDisplay.manaIncreaseMultiplier1;
        manaIncreaseMultiplier2 = manaDisplay.manaIncreaseMultiplier2;
        manaIncreaseMultiplier3 = manaDisplay.manaIncreaseMultiplier3;
        activated = false;
        cardFrameAttached = GetComponentInParent<CardFrame>();
        SetBeat();
    }

    public void SetBeat()
    {
        cardAttached = cardFrameAttached.cardObject;
        if(activated)
        {
            beatGenerator.SetBeatActivated(true);
            beatGenerator.InitializeBeat(modeBeat);
        }
    }

    public float MergeBeatCard(int beatNumber=1)
    {

        timeBeat = beatGenerator.GetBeat1Time(beatNumber);

        //Make it easier for mode "five"
        if(modeBeat == "five")
        {
            if(timeBeat <= 0.35)
            {
                timeBeat = timeBeat / 1.3f;
            }
            else if(timeBeat >= 0.65)
            {
                timeBeat = timeBeat * 1.15f;
            }
        }
        else if(modeBeat == "double") //harder for double slow
        {
            if (timeBeat <= 0.4)
            {
                timeBeat = timeBeat * 1.05f;
            }
            else if (timeBeat >= 0.6)
            {
                timeBeat = timeBeat / 1.05f;
            }
        }

        if (timeBeat < 0.03 || timeBeat > 0.97)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
            return 3f;
        }
        else if (timeBeat < 0.12 || timeBeat > 0.88)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
            return 2f;
        }
        else if (timeBeat < 0.17 || timeBeat > 0.83)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
            return 1f;
        }
        else if (timeBeat < 0.25 || timeBeat > 0.75)
        {
            return 0f;
        }
        else
        {
            cardAttached.ChangeCardMana(manaReductionMultiplier);
            return -1f;
        }
    }


    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
        if(activated)
        {
            SetBeatIcon();
        }
    }

    private void SetBeatIcon()
    {
        boxRenderer.gameObject.SetActive(true);
        noteRenderer.gameObject.SetActive(true);
    }

    public void SetModeBeat(string modeBeatSet)
    {
        modeBeat = modeBeatSet;
    }

    public string GetModeBeat()
    {
        return modeBeat;
    }

}
