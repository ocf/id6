use serenity::framework::standard::{macros::command, CommandResult, Args};
use serenity::model::channel::Message;
use serenity::prelude::*;
use scraper::{Html, Selector};

#[command]
pub async fn croads(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let meal = args.single::<String>().unwrap_or_default().to_lowercase();
    let response = get_croads_menu(&meal).await.unwrap_or_else(|_| "Failed to fetch menu.".to_string());
    msg.channel_id.say(&ctx.http, response).await?;
    Ok(())
}

async fn get_croads_menu(meal: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    let url = "https://dining.berkeley.edu/menus/";
    let res = reqwest::get(url).await?.text().await?;
    let document = Html::parse_document(&res);
    
    let crossroads_selector = Selector::parse("li.location-name.Crossroads").unwrap();
    let period_selector = Selector::parse("li.preiod-name").unwrap();
    let span_selector = Selector::parse("span").unwrap();
    let recipe_selector = Selector::parse("ul.recipe-name > li.recip > span:first-child").unwrap();

    let category_selector = Selector::parse("div.cat-name").unwrap();

    let mut lunch_items = Vec::new();
    let mut dinner_items = Vec::new();

    if let Some(croads_node) = document.select(&crossroads_selector).next() {
        for period in croads_node.select(&period_selector) {
            let period_name = period.select(&span_selector).next().map(|s| s.inner_html()).unwrap_or_default();
            
            let mut items = Vec::new();

            for category in period.select(&category_selector) {
                let category_name = category.select(&span_selector).next().map(|s| s.inner_html()).unwrap_or_default().to_lowercase();
                
                if category_name.contains("center plate") || category_name.contains("lemon grass") || category_name.contains("grill") {
                    for recipe in category.select(&recipe_selector) {
                        let text = recipe.inner_html();
                        let text = text.replace("&amp;", "&");
                        if !text.contains("<img") {
                            items.push(text.trim().to_string());
                        }
                    }
                }
            }

            if period_name.contains("Lunch") {
                lunch_items = items;
            } else if period_name.contains("Dinner") {
                dinner_items = items;
            }
        }
    }

    let include_lunch = meal == "lunch" || meal == "" || meal == "all";
    let include_dinner = meal == "dinner" || meal == "" || meal == "all";

    let mut response = String::new();
    
    if !include_lunch && !include_dinner {
        return Ok("Invalid option. Use `?croads lunch` or `?croads dinner`.".to_string());
    }

    response.push_str("**Crossroads Menu**\n\n");
    
    if include_lunch {
        response.push_str("**Lunch**\n");
        if lunch_items.is_empty() {
            response.push_str("No lunch menu found.\n");
        } else {
            for item in &lunch_items {
                response.push_str(&format!("- {}\n", item));
            }
        }
    }

    if include_lunch && include_dinner {
        response.push_str("\n");
    }

    if include_dinner {
        response.push_str("**Dinner**\n");
        if dinner_items.is_empty() {
            response.push_str("No dinner menu found.\n");
        } else {
            for item in &dinner_items {
                response.push_str(&format!("- {}\n", item));
            }
        }
    }

    if response.len() > 1900 {
        response.truncate(1900);
        response.push_str("...\n(Truncated due to length)");
    }

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_get_croads_menu() {
        let menu = get_croads_menu("").await.unwrap();
        println!("{}", menu);
        assert!(menu.contains("Crossroads Menu"));
    }
}
