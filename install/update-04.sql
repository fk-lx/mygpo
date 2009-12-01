-- replaced by mygpo.api.models.Device.latest_actions()
DROP VIEW IF EXISTS sync_group_subscription_log;
DROP VIEW IF EXISTS sync_group_current_subscription;


DELIMITER $$
DROP PROCEDURE IF EXISTS update_toplist $$
CREATE PROCEDURE update_toplist()
BEGIN
    DECLARE deadlock INT DEFAULT 0;
        DECLARE attempts INT DEFAULT 0;

    DROP TABLE IF EXISTS toplist_temp;
    CREATE TABLE toplist_temp (
            podcast_id INT PRIMARY KEY REFERENCES podcast (id),
            subscription_count INT NOT NULL DEFAULT 0,
            INDEX(podcast_id)
    );

    try_loop:WHILE (attempts<3) DO
    BEGIN
        DECLARE deadlock_detected CONDITION FOR 1213;
            DECLARE EXIT HANDLER FOR deadlock_detected
                BEGIN
                    ROLLBACK;
                    SET deadlock=1;
                END;
            SET deadlock=0;
               
            START TRANSACTION;
            DELETE FROM toplist_temp;
            INSERT INTO toplist_temp (SELECT a.podcast_id, COUNT(*) AS count_subscription
                        FROM (SELECT DISTINCT podcast_id, user_id 
                            FROM public_subscription) a 
                        GROUP BY podcast_id);
            DELETE FROM toplist;
            INSERT INTO toplist (SELECT podcast_id, subscription_count FROM toplist_temp
                        ORDER BY subscription_count DESC LIMIT 100);
            
            COMMIT;
        END;
        IF deadlock=0 THEN
                LEAVE try_loop;
            ELSE
                SET attempts=attempts+1;
            END IF;
            END WHILE try_loop;

        IF deadlock=1 THEN
            call FAIL('Toplist is not updated!');
        END IF;
        DROP TABLE IF EXISTS toplist_temp;

END $$
DELIMITER ;

-- converting the column subscription_log.action from varchar to tinyint(1)
alter table subscription_log add column action_tmp tinyint(1);
update subscription_log set action_tmp = 1 where action = 'subscribe';
update subscription_log set action_tmp = -1 where action = 'unsubscribe';
alter table subscription_log drop column action;
alter table subscription_log change action_tmp action tinyint(1);

CREATE UNIQUE INDEX unique_subscription_log ON subscription_log (device_id, podcast_id, timestamp);
CREATE UNIQUE INDEX unique_episode_lg ON episode_log (user_id, episode_id, timestamp);

DROP TRIGGER IF EXISTS episode_trig_unique;

DELIMITER //
CREATE TRIGGER episode_trig_unique BEFORE INSERT ON episode
FOR EACH ROW
BEGIN
    declare help_url INT;
    set help_url = 0;
  
       SELECT count(a.id) into help_url FROM episode a where a.url=new.url and a.podcast_id=new.podcast_id;

    IF help_url > 0 THEN
        call Fail('This episode already exists!');
    END IF;

END;//
DELIMITER ;


