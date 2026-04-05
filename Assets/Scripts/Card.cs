using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Card : MonoBehaviour
{

    [SerializeField] CardFrame cardFramePrefab;
    [SerializeField] public float cardType;
    [SerializeField] float cardMana;
    [SerializeField] public float cardCost;
    CardDrawer cardDrawer;
    ManaDisplay manaDisplay;
    public CardFrame cardFrame;
    public bool memoryCardFlag = false;
    LevelLoader levelLoader;

    private void Start()
    {
        cardDrawer = FindObjectOfType<CardDrawer>();
        manaDisplay = FindObjectOfType<ManaDisplay>();

        cardType = cardDrawer.GetCardType();
        cardCost = cardDrawer.GetCardCost();
        //cardType = PlayerPrefs.GetFloat("CardType");
        //cardCost = PlayerPrefs.GetFloat("CardCost");
        cardMana = Mathf.Round(cardCost * manaDisplay.manaReductionMultiplier);
        levelLoader = FindObjectOfType<LevelLoader>();

        cardFrame = Instantiate(cardFramePrefab, transform.position, transform.rotation) as CardFrame;
        cardFrame.SetCardObject(this);
        cardFrame.SetCardType(cardType);

    }

    public void InitCardFrame(CardFrame cardFrameInput=null)
    {
        if (cardFrameInput == null)
        {
            cardFrame = Instantiate(cardFramePrefab, transform.position, transform.rotation) as CardFrame;
        }
        else
        {
            cardFrame = cardFrameInput;
        }

        cardFrame.SetCardObject(this);
        cardFrame.SetCardType(cardType);
    }

    public float GetCardMana()
    {
        return cardMana;
    }

    public void ChangeCardMana(float manaMultiplier)
    {
        cardMana = Mathf.Round(cardMana * manaMultiplier);
        cardFrame.closestSlot.UpdateManaValue();
    }

    public CardFrame GetCardFrame()
    {
        return cardFrame;
    }

    public void SetCardFrame(CardFrame cardSet)
    {
        cardFrame = cardSet;
    }

    private void OnDestroy()
    {
        manaDisplay.AddMana(cardMana);
    }


    public CardInfo GetCardInfo()
    {
        float numberInfo = cardFrame.numberCard.numberSelected;

        Color colorValue = cardFrame.colorCard.colorSelected;
        int colorInfo;
        if (colorValue == Color.red)
        {
            colorInfo = 0;
        }
        else if (colorValue == Color.green)
        {
            colorInfo = 1;
        }
        else if (colorValue == Color.blue)
        {
            colorInfo = 2;
        }
        else if (colorValue == Color.cyan)
        {
            colorInfo = 3;
        }
        else if (colorValue == Color.magenta)
        {
            colorInfo = 4;
        }
        else if (colorValue == Color.yellow)
        {
            colorInfo = 5;
        }
        else if (colorValue == Color.clear)
        {
            colorInfo = 6;
        }
        else
        {
            colorInfo = 7;
        }

        int shapeInfo = cardFrame.shapeCard.spriteSelectedIndex;

        List<string> wordInfo = cardFrame.wordCard.wordSelectedList;

        float cardMana = GetCardMana();

        int sceneIndex = levelLoader.currentSceneIndex;

        CardInfo cardInfo = new CardInfo();
        cardInfo.gameIndex = 1;
        cardInfo.sceneIndex = sceneIndex;
        cardInfo.cardMana = cardMana;
        cardInfo.numberInfo = numberInfo;
        cardInfo.colorInfo = colorInfo;
        cardInfo.shapeInfo = shapeInfo;
        cardInfo.wordInfo = wordInfo;

        return cardInfo;

    }

    public class CardInfo
    {
        public int gameIndex { get; set; }
        public int sceneIndex { get; set; }
        public float cardMana { get; set; }
        public float numberInfo { get; set; }
        public int colorInfo { get; set; }
        public int shapeInfo { get; set; }
        public List<string> wordInfo { get; set; }
    }

    public Card ShallowCopy()
    {
        return (Card) this.MemberwiseClone();
    }

}
