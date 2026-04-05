using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ShapeCard : MonoBehaviour
{
    [SerializeField] public Sprite spriteSelected;
    [SerializeField] Sprite[] spriteListTriangle;
    [SerializeField] Sprite[] spriteListSquare;
    [SerializeField] Sprite[] spriteListTriple;
    [SerializeField] Sprite[] spriteListKanizsa;
    [SerializeField] Sprite[] spriteListSphere;
    [SerializeField] Sprite[] spriteListHanoi;
    [SerializeField] bool activated = false;
    Sprite[] spriteListSelected;

    public int spriteSelectedIndex;
    SpriteRenderer spriteRendererShape;
    Sprite spriteInitial;
    CardFrame cardFrameAttached;
    Card cardAttached;
    ManaDisplay manaDisplay;
    float manaReductionMultiplier;
    float manaIncreaseMultiplier1;
    float manaIncreaseMultiplier2;
    float manaIncreaseMultiplier3;
    bool cardSuper;
    string modeShape = "triangle";

    void Start()
    {
        manaDisplay = FindObjectOfType<ManaDisplay>();
        manaReductionMultiplier = manaDisplay.manaReductionMultiplier;
        manaIncreaseMultiplier1 = manaDisplay.manaIncreaseMultiplier1;
        manaIncreaseMultiplier2 = manaDisplay.manaIncreaseMultiplier2;
        manaIncreaseMultiplier3 = manaDisplay.manaIncreaseMultiplier3;
        activated = false;
        cardFrameAttached = GetComponentInParent<CardFrame>();
        cardSuper = cardFrameAttached.cardSuper;
        cardAttached = cardFrameAttached.cardObject;
        SetShapesForMode();
        spriteInitial = SetShape();
    }

    public void SetShapesForMode()
    {
        if (modeShape == "triangle")
        {
            spriteListSelected = spriteListTriangle;
        }
        else if(modeShape == "rectangle")
        {
            spriteListSelected = spriteListSquare;
        }
        else if (modeShape == "triple")
        {
            spriteListSelected = spriteListTriple;
        }
        else if (modeShape == "kanizsa")
        {
            spriteListSelected = spriteListKanizsa;
        }
        else if (modeShape == "sphere")
        {
            spriteListSelected = spriteListSphere;
        }
        else if (modeShape == "hanoi")
        {
            spriteListSelected = spriteListHanoi;
        }

    }

    public Sprite SetShape()
    {
        spriteRendererShape =
                GetComponentInChildren<SpriteRenderer>();

        if (modeShape == "triangle" || modeShape == "rectangle" || modeShape == "triple" || modeShape == "kanizsa")
        {
            spriteSelectedIndex = 8;
            spriteSelected = spriteListSelected[8];
            if (activated)
            {
                spriteSelectedIndex = Random.Range(0, spriteListSelected.Length - 2);
                spriteSelected = spriteListSelected[spriteSelectedIndex];
            }
            if (cardSuper) //WARNING. Deprecated!
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[7];
            }
            spriteRendererShape.sprite = spriteSelected;
        }
        else if (modeShape == "sphere")
        {
            spriteSelectedIndex = 10;
            spriteSelected = spriteListSelected[10];
            if (activated)
            {
                spriteSelectedIndex = Random.Range(1, spriteListSelected.Length - 2);
                spriteSelected = spriteListSelected[spriteSelectedIndex];
            }
            spriteRendererShape.sprite = spriteSelected;
            spriteRendererShape.color = Color.white;
        }
        else if (modeShape == "hanoi")
        {
            spriteSelectedIndex = 16;
            spriteSelected = spriteListSelected[16];
            if (activated)
            {
                do
                {
                    spriteSelectedIndex = Random.Range(0, spriteListSelected.Length - 2);
                } while (spriteSelectedIndex == 9);

                spriteSelected = spriteListSelected[spriteSelectedIndex];
                spriteRendererShape.sprite = spriteSelected;
                spriteRendererShape.color = Color.white;
            }
        }

        

        return spriteSelected;
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
    }


    public float ComputeMergeShapeGain(int spriteNewIndex)
    {
        if (modeShape == "triangle" || modeShape == "rectangle" || modeShape == "triple" || modeShape == "kanizsa")
        {
            if (spriteNewIndex == 8)
            {
                return 0f;
            }

            if (spriteSelectedIndex == 8 && spriteNewIndex != 8)
            {
                return 0f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 7)
            {
                return 3f;
            }

            if (spriteSelectedIndex == 7 && spriteNewIndex != 7)
            {
                return -1f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 7)
            {
                return 2f;
            }

            if (spriteSelectedIndex != 7 && spriteNewIndex == 7)
            {
                return 0f;
            }


            if (spriteSelectedIndex == 0 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                return 1f;
            }
        }

        else if (modeShape == "sphere")
        {


            if (spriteNewIndex == 10)
            {
                return 0f;
            }

            if (spriteSelectedIndex == 10 && spriteNewIndex != 10)
            {
                return 0f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 0)
            {
                return 3f;
            }

            if (spriteSelectedIndex == 0 && spriteNewIndex != 0)
            {
                return -1f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 0)
            {
                return 0f;
            }

            if (spriteSelectedIndex != 0 && spriteNewIndex == 0)
            {
                return 0f;
            }

            //Logic starts here
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 7)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 8)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 7)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 8)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 7)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 8)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 7)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 8)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 5)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 8)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 4)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 7)
            {
                return 1f;
            }
        }

        else if (modeShape == "hanoi")
        {
            if (spriteNewIndex == 16)
            {
                return 0f;
            }

            if (spriteSelectedIndex == 16 && spriteNewIndex != 16)
            {
                return 0f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 9)
            {
                return 3f;
            }

            if (spriteSelectedIndex == 9 && spriteNewIndex != 9)
            {
                return -1f;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 9)
            {
                return -1f;
            }

            if (spriteSelectedIndex != 9 && spriteNewIndex == 9)
            {
                return 0f;
            }

            //Logic starts here

            if (spriteSelectedIndex == 0 && spriteNewIndex == 1)
            {

                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 9)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 11)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 12)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 9)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 9)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 10)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 13)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 0)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 7)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 8)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 9)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 10)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 11)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 12)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 13)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 14)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 0)
            {
                return 2f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 8)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 9)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 10)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 11)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 12)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 13)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 14)
            {
                return -1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 3)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 5)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 4)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 7)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 0)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 13)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 2)
            {
                return 1f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 14)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 0)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 1)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 2)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 3)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 4)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 5)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 6)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 7)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 8)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 9)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 10)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 11)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 12)
            {
                return 0f;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 13)
            {
                return 0f;
            }
        }

        return 0f;
    }

    public void MergeShapeCard(int spriteNewIndex)
    {
        if (modeShape == "triangle" || modeShape == "rectangle" || modeShape == "triple" || modeShape == "kanizsa")
        {
            if (spriteNewIndex == 8)
            {
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 8 && spriteNewIndex != 8)
            {
                spriteSelectedIndex = spriteNewIndex;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 7)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 7 && spriteNewIndex != 7)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 7)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex != 7 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }


            if (spriteSelectedIndex == 0 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
        }

        else if (modeShape == "sphere")
        {
            if (spriteNewIndex == 10)
            {
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 10 && spriteNewIndex != 10)
            {
                spriteSelectedIndex = spriteNewIndex;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 0)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 0 && spriteNewIndex != 0)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 0)
            {
                return;
            }

            if (spriteSelectedIndex != 0 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            //Logic starts here
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }


        }

        else if (modeShape == "hanoi")
        {
            if (spriteNewIndex == 16)
            {
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 16 && spriteNewIndex != 16)
            {
                spriteSelectedIndex = spriteNewIndex;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex == 9)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == 9 && spriteNewIndex != 9)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex == spriteNewIndex && spriteSelectedIndex != 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            if (spriteSelectedIndex != 9 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }

            //Logic starts here

            if (spriteSelectedIndex == 0 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 12;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 14;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 0 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 10;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 13;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 1 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 9;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 11;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 2 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 13;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 3 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 11;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 4 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 14;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 5 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 9;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 6 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 12;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 7 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 10;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 8 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 10 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 4;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 11 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 6;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 12 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 3;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 13 && spriteNewIndex == 14)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 0)
            {
                spriteSelectedIndex = 8;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 1)
            {
                spriteSelectedIndex = 7;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 2)
            {
                spriteSelectedIndex = 5;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 3)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 4)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 5)
            {
                spriteSelectedIndex = 2;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 6)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 7)
            {
                spriteSelectedIndex = 1;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 8)
            {
                spriteSelectedIndex = 0;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 9)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 10)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 11)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 12)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
            if (spriteSelectedIndex == 14 && spriteNewIndex == 13)
            {
                spriteSelectedIndex = 16;
                spriteSelected = spriteListSelected[spriteSelectedIndex];
                SetShapeCard(spriteSelectedIndex);
                return;
            }
        }

    }

    public void SetShapeCard(int spriteCardIndex)
    {
        spriteRendererShape.sprite = spriteListSelected[spriteCardIndex];
    }

    public void SetModeShape(string modeShapeSet)
    {
        modeShape = modeShapeSet;
        SetShapesForMode();
    }

    public string GetModeShape()
    {
        return modeShape;
    }

}
