-- claim_inventory.lua

-- KEYS[1] is the stock, KEYS[2] is the set of users who already bought.
if redis.call("SISMEMBER", KEYS[2], ARGV[1]) == 1 then
    return -2 
end

local stock = redis.call("GET", KEYS[1])
if not stock then
    return -3
end

stock = tonumber(stock)

if stock <= 0 then
    return -1
end

local new_stock = redis.call("DECR", KEYS[1])
redis.call("SADD", KEYS[2], ARGV[1])

local order_payload = cjson.encode({
    order_id = ARGV[2],
    user_id = ARGV[1],
    item_id = KEYS[1],
    ts = redis.call("TIME")[1]
})
redis.call("RPUSH", "orders:queue", order_payload)

return new_stock
